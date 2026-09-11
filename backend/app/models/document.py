from dataclasses import dataclass


@dataclass
class Document:
    id: int | None
    document_name: str
    document_type: str
    status: str
    result_json: str
    created_at: str