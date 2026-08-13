import asyncio
from unittest.mock import MagicMock, patch

from shared.exceptions.error_handlers import domain_error_handler, unhandled_exception_handler
from shared.exceptions.exceptions import DomainError, PermissionDenied


def _run(coro):
    return asyncio.run(coro)


class TestDomainErrorHandler:
    def test_records_exception_and_attributes_on_span(self):
        exc = DomainError("Budget line amount cannot be negative", status_code=400)
        mock_span = MagicMock()

        with patch(
            "shared.exceptions.error_handlers.trace.get_current_span", return_value=mock_span
        ):
            response = _run(domain_error_handler(MagicMock(), exc))

        mock_span.record_exception.assert_called_once_with(exc)
        assert response.status_code == 400
        assert response.body == b'{"detail":"Budget line amount cannot be negative"}'

    def test_records_exception_type_and_message(self):
        exc = DomainError("Budget line amount cannot be negative", status_code=400)

        with patch("shared.exceptions.error_handlers.set_span_attributes") as mock_set_span_attrs:
            _run(domain_error_handler(MagicMock(), exc))

        mock_set_span_attrs.assert_called_once_with(
            **{
                "error.type": "DomainError",
                "error.message": "Budget line amount cannot be negative",
            }
        )

    def test_permission_denied_records_span(self):
        exc = PermissionDenied()
        mock_span = MagicMock()

        with patch(
            "shared.exceptions.error_handlers.trace.get_current_span", return_value=mock_span
        ):
            response = _run(domain_error_handler(MagicMock(), exc))

        mock_span.record_exception.assert_called_once_with(exc)
        assert response.status_code == 400


class TestUnhandledExceptionHandler:
    def test_records_exception_and_returns_generic_500(self):
        exc = AttributeError("'NoneType' object has no attribute 'foo'")
        mock_span = MagicMock()

        with patch(
            "shared.exceptions.error_handlers.trace.get_current_span", return_value=mock_span
        ):
            response = _run(unhandled_exception_handler(MagicMock(), exc))

        mock_span.record_exception.assert_called_once_with(exc)
        assert response.status_code == 500
        assert response.body == b'{"detail":"Internal server error"}'

    def test_records_exception_type_and_message_without_leaking_to_response(self):
        exc = AttributeError("'NoneType' object has no attribute 'foo'")

        with patch("shared.exceptions.error_handlers.set_span_attributes") as mock_set_span_attrs:
            response = _run(unhandled_exception_handler(MagicMock(), exc))

        mock_set_span_attrs.assert_called_once_with(
            **{
                "error.type": "AttributeError",
                "error.message": "'NoneType' object has no attribute 'foo'",
            }
        )
        assert b"NoneType" not in response.body
