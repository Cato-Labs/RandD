from __future__ import annotations

import inspect

from app.vantage.pg_repository import PostgresVantageRepository


def test_postgres_repository_exposes_live_home_domain_surface() -> None:
    expected = {
        "list_portfolios",
        "create_portfolio",
        "create_home",
        "record_asset_document",
        "list_asset_documents",
        "record_asset_research_value",
        "list_asset_research_values",
    }
    assert expected <= set(dir(PostgresVantageRepository))
    create_home = inspect.signature(PostgresVantageRepository.create_home)
    assert list(create_home.parameters)[:6] == [
        "self", "organization_id", "user_id", "portfolio_id", "name", "client_id"
    ]
    create_asset = inspect.signature(PostgresVantageRepository.create_asset)
    assert any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in create_asset.parameters.values())
