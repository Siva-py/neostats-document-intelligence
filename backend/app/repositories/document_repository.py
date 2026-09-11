import json

from datetime import datetime, timezone

from app.core.database import get_connection


class DocumentRepository:

    def save_document(
        self,
        document_name: str,
        document_type: str,
        status: str,
        result: dict,
    ):
        connection = get_connection()

        try:
            created_at = datetime.now(
                timezone.utc
            ).isoformat()

            result_json = json.dumps(
                result,
                ensure_ascii=False,
            )

            connection.execute(
                """
                INSERT INTO documents (
                    document_name,
                    document_type,
                    status,
                    result_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(document_name)
                DO UPDATE SET
                    document_type = excluded.document_type,
                    status = excluded.status,
                    result_json = excluded.result_json,
                    created_at = excluded.created_at
                """,
                (
                    document_name,
                    document_type,
                    status,
                    result_json,
                    created_at,
                ),
            )

            connection.commit()

        finally:
            connection.close()

    def get_document(
        self,
        document_name: str,
    ):
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM documents
                WHERE document_name = ?
                """,
                (document_name,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_dict(row)

        finally:
            connection.close()

    def get_all_documents(self):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT
                    id,
                    document_name,
                    document_type,
                    status,
                    created_at
                FROM documents
                ORDER BY created_at DESC
                """
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

        finally:
            connection.close()

    def _row_to_dict(self, row):
        result = dict(row)

        result["result"] = json.loads(
            result.pop("result_json")
        )

        return result