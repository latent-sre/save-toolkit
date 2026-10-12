// Reference solution for the Go incidents scenario, built on backend-craft's house.go starter.
package main

import (
	"context"
	"encoding/hex"
	"net/http"
	"time"

	"github.com/danielgtaylor/huma/v2"
)

const maxPageSize = 200

type IncidentOut struct {
	ID        string    `json:"id"`
	Status    string    `json:"status"`
	Title     string    `json:"title"`
	Service   string    `json:"service"`
	CreatedAt time.Time `json:"created_at"`
}

type IncidentPage Page[IncidentOut]

func out(i Incident) IncidentOut {
	return IncidentOut{ID: i.ID, Status: i.Status, Title: i.Title, Service: i.Service, CreatedAt: i.CreatedAt}
}

type ListIncidentsInput struct {
	Cursor string `query:"cursor" pattern:"^([0-9a-f]{2})+$" maxLength:"2048" doc:"Opaque cursor from next_cursor."`
	Limit  int    `query:"limit" minimum:"1" default:"50" doc:"Page size; values above 200 are lowered to 200."`
	Status string `query:"status" enum:"open,closed"`
}

func (in *ListIncidentsInput) Resolve(ctx huma.Context) []error {
	u := ctx.URL()
	if q := u.Query(); q.Has("cursor") && q.Get("cursor") == "" {
		return []error{&huma.ErrorDetail{Location: "query.cursor", Message: "expected a cursor from next_cursor"}}
	}
	return nil
}

type ListIncidentsOutput struct{ Body IncidentPage }

type GetIncidentInput struct {
	ID string `path:"id" maxLength:"64"`
}

type GetIncidentOutput struct{ Body IncidentOut }

func registerIncidents(api huma.API) {
	huma.Register(api, huma.Operation{
		OperationID: "listIncidents", Method: http.MethodGet, Path: "/v1/incidents",
		Summary: "List incidents, one cursor page at a time.", Security: Bearer,
		Errors: []int{http.StatusUnauthorized, http.StatusUnprocessableEntity},
	}, func(ctx context.Context, in *ListIncidentsInput) (*ListIncidentsOutput, error) {
		after, _ := hex.DecodeString(in.Cursor)
		limit := min(in.Limit, maxPageSize)
		rows := []IncidentOut{}
		for _, i := range Incidents {
			if i.ID > string(after) && (in.Status == "" || i.Status == in.Status) {
				rows = append(rows, out(i))
				if len(rows) == limit+1 {
					break
				}
			}
		}
		page := IncidentPage{Data: rows}
		if len(rows) > limit {
			page.Data = rows[:limit]
			next := hex.EncodeToString([]byte(page.Data[limit-1].ID))
			page.NextCursor = &next
		}
		return &ListIncidentsOutput{Body: page}, nil
	})

	huma.Register(api, huma.Operation{
		OperationID: "getIncident", Method: http.MethodGet, Path: "/v1/incidents/{id}",
		Summary: "Get one incident.", Security: Bearer,
		Errors: []int{http.StatusUnauthorized, http.StatusNotFound, http.StatusUnprocessableEntity},
	}, func(ctx context.Context, in *GetIncidentInput) (*GetIncidentOutput, error) {
		for _, i := range Incidents {
			if i.ID == in.ID {
				return &GetIncidentOutput{Body: out(i)}, nil
			}
		}
		return nil, huma.Error404NotFound("No incident with that id.")
	})
}
