"""Route-level wiring checks for mapping_routes.py's business-context span
attributes. mapping_routes.py has no update/delete endpoints, so this
covers two representative create endpoints (donor templates, donor fields)
using their own natural ids per the design decision — not budget_id."""

from types import SimpleNamespace
from unittest.mock import patch


class TestMappingRoutesWiring:
    def test_create_template_route_sets_donor_template_id_span_attribute(self, make_client):
        client = make_client()
        with (
            patch(
                "app.api.mapping_routes.create_donor_template",
                return_value=SimpleNamespace(id=7, name="Acme Template"),
            ),
            patch("app.api.mapping_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post("/api/v1/donor-mapping/templates", json={"name": "Acme Template"})
        mock_set_span_attrs.assert_any_call(donor_template_id=7)

    def test_create_field_route_sets_span_attributes(self, make_client):
        client = make_client()
        with (
            patch(
                "app.api.mapping_routes.get_donor_template",
                return_value=SimpleNamespace(id=7, name="Acme Template"),
            ),
            patch(
                "app.api.mapping_routes.create_donor_field",
                return_value=SimpleNamespace(id=3, donor_template_id=7, field_name="Amount"),
            ),
            patch("app.api.mapping_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/donor-mapping/fields",
                json={"donor_template_id": 7, "field_name": "Amount"},
            )
        mock_set_span_attrs.assert_any_call(donor_template_id=7)
        mock_set_span_attrs.assert_any_call(donor_field_id=3)
