// An example resource carrying the whole house contract: explicit operation IDs, /v1 paths,
// bearer security, a cursor page whose oversized limit is lowered, a 404 problem for a missing or
// unpermitted object, and named body types. Replace Thing and ThingStore with the real resource.
package main

import (
	"context"
	"encoding/hex"
	"net/http"
	"slices"
	"strings"
	"sync"

	"github.com/danielgtaylor/huma/v2"
)

const maxPageSize = 200

type Thing struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Team string `json:"team"`
}

// ThingStore stands in for the datastore; the real one queries with an index on ID.
type ThingStore struct {
	mu       sync.RWMutex
	things   []Thing // ordered by ID, the page order
	readyErr error   // stands in for a failed dependency check
}

func NewThingStore(things ...Thing) *ThingStore {
	sorted := slices.Clone(things)
	slices.SortFunc(sorted, func(a, b Thing) int { return strings.Compare(a.ID, b.ID) })
	return &ThingStore{things: sorted}
}

// Ready reports whether this instance can serve: here, always; with a database, a short ping.
func (s *ThingStore) Ready(context.Context) error { return s.readyErr }

// After returns up to limit things the principal may read, with IDs after the given one.
func (s *ThingStore) After(_ context.Context, p Principal, afterID string, limit int) []Thing {
	s.mu.RLock()
	defer s.mu.RUnlock()
	page := []Thing{}
	for _, t := range s.things {
		if t.ID > afterID && canRead(p, t) {
			page = append(page, t)
			if len(page) == limit {
				break
			}
		}
	}
	return page
}

func (s *ThingStore) Get(_ context.Context, id string) (Thing, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, t := range s.things {
		if t.ID == id {
			return t, true
		}
	}
	return Thing{}, false
}

// canRead is the object-level rule: a principal reads the things of the teams in its scopes.
func canRead(p Principal, t Thing) bool {
	return slices.Contains(p.Scopes, "team:"+t.Team)
}

// A defined type, not an alias, so the document names the schema ThingPage.
type ThingPage Page[Thing]

type ListThingsInput struct {
	Cursor string `query:"cursor" pattern:"^([0-9a-f]{2})+$" maxLength:"2048" doc:"Opaque cursor from next_cursor; omit for the first page."`
	Limit  int    `query:"limit" minimum:"1" default:"50" doc:"Page size; values above 200 are lowered to 200."`
}

// Resolve rejects ?cursor= with no value: Huma reads an empty query value as absent and skips its
// validation, while the document says a present cursor matches the pattern.
func (in *ListThingsInput) Resolve(ctx huma.Context) []error {
	u := ctx.URL()
	if query := u.Query(); query.Has("cursor") && query.Get("cursor") == "" {
		return []error{&huma.ErrorDetail{Location: "query.cursor", Message: "expected a cursor from next_cursor"}}
	}
	return nil
}

type ListThingsOutput struct{ Body ThingPage }

type GetThingInput struct {
	ID string `path:"id" maxLength:"64"`
}

type GetThingOutput struct{ Body Thing }

// The document declares exactly the cursors the service accepts: every string matching the
// pattern decodes, and anything else is a 422 from validation. A cursor the service never issued
// only moves the page start; authorization still filters every row.
func encodeCursor(id string) string { return hex.EncodeToString([]byte(id)) }

func decodeCursor(cursor string) string {
	b, _ := hex.DecodeString(cursor) // the pattern guarantees valid hex
	return string(b)
}

func registerThings(api huma.API, store *ThingStore) {
	huma.Register(api, huma.Operation{
		OperationID: "listThings",
		Method:      http.MethodGet,
		Path:        "/v1/things",
		Summary:     "List the things the caller may read, one cursor page at a time.",
		Security:    Bearer,
		Errors:      []int{http.StatusUnauthorized, http.StatusUnprocessableEntity},
	}, func(ctx context.Context, in *ListThingsInput) (*ListThingsOutput, error) {
		principal, _ := PrincipalFrom(ctx)
		after := decodeCursor(in.Cursor)
		limit := min(in.Limit, maxPageSize)
		rows := store.After(ctx, principal, after, limit+1) // one extra row says whether more exist
		page := ThingPage{Data: rows}
		if len(rows) > limit {
			page.Data = rows[:limit]
			next := encodeCursor(page.Data[limit-1].ID)
			page.NextCursor = &next
		}
		return &ListThingsOutput{Body: page}, nil
	})

	huma.Register(api, huma.Operation{
		OperationID: "getThing",
		Method:      http.MethodGet,
		Path:        "/v1/things/{id}",
		Summary:     "Get one thing.",
		Security:    Bearer,
		Errors:      []int{http.StatusUnauthorized, http.StatusNotFound, http.StatusUnprocessableEntity},
	}, func(ctx context.Context, in *GetThingInput) (*GetThingOutput, error) {
		principal, _ := PrincipalFrom(ctx)
		thing, found := store.Get(ctx, in.ID)
		if !found || !canRead(principal, thing) { // a thing the caller may not read does not exist for it
			return nil, huma.Error404NotFound("No thing with that ID.")
		}
		return &GetThingOutput{Body: thing}, nil
	})
}
