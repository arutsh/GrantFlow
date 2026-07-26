import factory
from uuid import uuid4

from app.models.report import AttachmentModel


class AttachmentFactory(factory.Factory):
    class Meta:
        model = AttachmentModel

    id = factory.LazyFunction(uuid4)
    report_line_id = factory.LazyFunction(uuid4)
    filename = "receipt.pdf"
    content_type = "application/pdf"
    size = 1024
    storage_key = factory.LazyAttribute(lambda o: f"attachments/test/{uuid4()}.pdf")
    created_by = factory.LazyFunction(uuid4)
    updated_by = factory.LazyFunction(uuid4)
    created_at = None
    updated_at = None
