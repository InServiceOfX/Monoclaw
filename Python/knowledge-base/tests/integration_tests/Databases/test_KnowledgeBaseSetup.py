"""
Integration tests for KnowledgeBaseSetup and KnowledgeBaseInterface.

USAGE:
Ensure a pgvector-enabled PostgreSQL instance is reachable at localhost:5432
with credentials inserviceofx/inserviceofx. A convenient way:

    docker run -d --name kb-postgres -p 5432:5432 \
        -e POSTGRES_USER=inserviceofx \
        -e POSTGRES_PASSWORD=inserviceofx \
        pgvector/pgvector:pg16

Then run tests from the project root:
    pytest tests/integration_tests/Databases/test_KnowledgeBaseSetup.py -v
"""

from pathlib import Path
from knowledge_base.Databases.Configuration import (
    KnowledgeBaseSetupData,
    KnowledgeBaseSetup,
)
from knowledge_base.Databases.PostgreSQLInterface import KnowledgeBaseInterface
import pytest

test_configuration_path = Path(__file__).parents[2] / \
    "TestSetup" / "knowledge_base_test_configuration.yml"

test_setup_data = KnowledgeBaseSetupData.from_yaml(test_configuration_path)


def test_KnowledgeBaseSetupData_from_yaml_works():
    assert test_setup_data.database_port == 5432
    assert test_setup_data.ip_address is not None
    assert test_setup_data.postgres_user == "inserviceofx"
    assert test_setup_data.postgres_password == "inserviceofx"
    assert test_setup_data.database_names == \
        {"KnowledgeBase": "test_knowledge_base"}


def test_KnowledgeBaseSetupData_from_default_values_works():
    data = KnowledgeBaseSetupData.from_default_values()
    assert data.database_port == 5432
    assert data.ip_address == "localhost"
    assert data.postgres_user == "inserviceofx"
    assert data.postgres_password == "inserviceofx"
    assert "KnowledgeBase" in data.database_names


def test_KnowledgeBaseSetupData_get_dsn_works():
    data = KnowledgeBaseSetupData.from_default_values()
    dsn = data.get_dsn()
    assert dsn.startswith("postgresql://")
    assert "inserviceofx" in dsn
    assert "localhost" in dsn
    assert "5432" in dsn


@pytest.mark.asyncio
async def test_KnowledgeBaseSetup_creates_postgresql_connection_from_database_type():
    setup = KnowledgeBaseSetup(test_setup_data)
    setup.create_postgresql_connection(database_type="KnowledgeBase")
    database_name = test_setup_data.database_names["KnowledgeBase"]

    assert await setup._connections["KnowledgeBase"].database_exists(
        database_name) is False, \
        f"Database {database_name} should not exist yet!"

    await setup._connections["KnowledgeBase"].create_database(database_name)

    assert await setup._connections["KnowledgeBase"].database_exists(
        database_name) is True, \
        f"Database {database_name} should exist now!"

    await setup._connections["KnowledgeBase"].drop_database(database_name)

    assert await setup._connections["KnowledgeBase"].database_exists(
        database_name) is False, \
        f"Database {database_name} should not exist now!"


@pytest.mark.asyncio
async def test_KnowledgeBaseSetup_create_pool_for_database_creates():
    setup = KnowledgeBaseSetup(test_setup_data)
    setup.create_postgresql_connection(database_type="KnowledgeBase")
    database_name = test_setup_data.database_names["KnowledgeBase"]

    assert await setup._connections["KnowledgeBase"].database_exists(
        database_name) is False, \
        f"Database {database_name} should not exist yet!"

    await setup.create_pool_for_database(database_type="KnowledgeBase")

    assert await setup._connections["KnowledgeBase"].database_exists(
        database_name) is True, \
        f"Database {database_name} should exist now!"

    # Verify vector extension was created
    extension_exists = await setup._connections["KnowledgeBase"].extension_exists(
        "vector")
    assert extension_exists is True, "pgvector extension should exist"

    await setup._connections["KnowledgeBase"].drop_database(database_name)

    assert await setup._connections["KnowledgeBase"].database_exists(
        database_name) is False, \
        f"Database {database_name} should not exist now!"


@pytest.mark.asyncio
async def test_KnowledgeBaseInterface_create_tables():
    setup = KnowledgeBaseSetup(test_setup_data)
    setup.create_postgresql_connection(database_type="KnowledgeBase")
    database_name = test_setup_data.database_names["KnowledgeBase"]

    await setup.create_pool_for_database(database_type="KnowledgeBase")
    connection = setup._connections["KnowledgeBase"]

    try:
        interface = KnowledgeBaseInterface(connection)
        success = await interface.create_tables()
        assert success is True, "create_tables should return True"

        docs_exist = await interface.table_exists("knowledge_base_documents")
        assert docs_exist is True, "knowledge_base_documents table should exist"

        chunks_exist = await interface.table_exists("knowledge_base_chunks")
        assert chunks_exist is True, "knowledge_base_chunks table should exist"
    finally:
        await connection.drop_database(database_name)


@pytest.mark.asyncio
async def test_KnowledgeBaseInterface_insert_and_retrieve_document():
    setup = KnowledgeBaseSetup(test_setup_data)
    setup.create_postgresql_connection(database_type="KnowledgeBase")
    database_name = test_setup_data.database_names["KnowledgeBase"]

    await setup.create_pool_for_database(database_type="KnowledgeBase")
    connection = setup._connections["KnowledgeBase"]

    try:
        interface = KnowledgeBaseInterface(connection)
        await interface.create_tables()

        doc_id = await interface.insert_document(
            title="Test Document",
            source_path="/tmp/test.txt",
            source_type="text",
            raw_content="This is test content.",
            content_hash="abc123def456" + "0" * 52,
            metadata={"key": "value"}
        )
        assert doc_id is not None, "insert_document should return an id"

        doc = await interface.get_document_by_id(doc_id)
        assert doc is not None
        assert doc["title"] == "Test Document"
        assert doc["source_type"] == "text"
        assert doc["raw_content"] == "This is test content."

        exists = await interface.document_exists_by_hash("abc123def456" + "0" * 52)
        assert exists is True

        not_exists = await interface.document_exists_by_hash("nonexistent" + "0" * 53)
        assert not_exists is False
    finally:
        await connection.drop_database(database_name)


@pytest.mark.asyncio
async def test_KnowledgeBaseInterface_insert_chunk_and_similarity_search():
    setup = KnowledgeBaseSetup(test_setup_data)
    setup.create_postgresql_connection(database_type="KnowledgeBase")
    database_name = test_setup_data.database_names["KnowledgeBase"]

    await setup.create_pool_for_database(database_type="KnowledgeBase")
    connection = setup._connections["KnowledgeBase"]

    try:
        interface = KnowledgeBaseInterface(connection)
        await interface.create_tables()

        doc_id = await interface.insert_document(
            title="Vector Test Doc",
            source_path=None,
            source_type="text",
            raw_content="Chunk embedding test.",
            content_hash="vectortest" + "0" * 54,
            metadata=None
        )
        assert doc_id is not None

        embedding = [0.1] * 1024  # Dummy 1024-dim vector
        chunk_id = await interface.insert_chunk(
            document_id=doc_id,
            chunk_index=0,
            total_chunks=1,
            content="Chunk embedding test.",
            content_hash="chunktest" + "0" * 55,
            embedding=embedding
        )
        assert chunk_id is not None

        chunks = await interface.get_document_chunks(doc_id)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Chunk embedding test."

        results = await interface.vector_similarity_search(
            query_embedding=embedding,
            limit=5
        )
        assert len(results) >= 1
        assert results[0]["document_id"] == doc_id
        assert "similarity_score" in results[0]
    finally:
        await connection.drop_database(database_name)
