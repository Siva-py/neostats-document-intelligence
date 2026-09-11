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

            connection.cursor().execute(
                """
                INSERT INTO documents (
                    document_name,
                    document_type,
                    status,
                    result_json,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(document_name)
                DO UPDATE SET
                    document_type = EXCLUDED.document_type,
                    status = EXCLUDED.status,
                    result_json = EXCLUDED.result_json,
                    created_at = EXCLUDED.created_at
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
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    document_name,
                    document_type,
                    status,
                    result_json,
                    created_at
                FROM documents
                WHERE document_name = %s
                """,
                (document_name,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_dict(row)

        finally:
            connection.close()

    def get_all_documents(self):
        connection = get_connection()

        try:
            cursor = connection.cursor()
            cursor.execute(
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
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "document_name": row[1],
                    "document_type": row[2],
                    "status": row[3],
                    "created_at": row[4],
                }
                for row in rows
            ]

        finally:
            connection.close()

    def _row_to_dict(self, row):
        result = {
            "id": row[0],
            "document_name": row[1],
            "document_type": row[2],
            "status": row[3],
            "result_json": row[4],
            "created_at": row[5],
        }

        result["result"] = json.loads(
            result.pop("result_json")
        )

        return result