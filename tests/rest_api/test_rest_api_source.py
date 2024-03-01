import dlt
import pytest

from sources.rest_api import SinglePagePaginator, rest_api_source
from tests.utils import ALL_DESTINATIONS, assert_load_info, load_table_counts


def _make_pipeline(destination_name: str):
    return dlt.pipeline(
        pipeline_name="rest_api",
        destination=destination_name,
        dataset_name="rest_api_data",
        full_refresh=True,
    )


@pytest.mark.parametrize("destination_name", ALL_DESTINATIONS)
def test_rest_api_source(destination_name: str) -> None:
    config = {
        "client": {
            "base_url": "https://pokeapi.co/api/v2/",
        },
        "resource_defaults": {
            "endpoint": {
                "params": {
                    "limit": 1000,
                },
            }
        },
        "resources": [
            {
                "name": "pokemon_list",
                "endpoint": "pokemon",
            },
            "berry",
            "location",
        ],
    }
    data = rest_api_source(config)
    pipeline = _make_pipeline(destination_name)
    load_info = pipeline.run(data)
    print(load_info)
    assert_load_info(load_info)
    table_names = [t["name"] for t in pipeline.default_schema.data_tables()]
    table_counts = load_table_counts(pipeline, *table_names)

    assert table_counts.keys() == {"pokemon_list", "berry", "location"}

    assert table_counts["pokemon_list"] == 1302
    assert table_counts["berry"] == 64
    assert table_counts["location"] == 1036


@pytest.mark.parametrize("destination_name", ALL_DESTINATIONS)
def test_dependent_resource(destination_name: str) -> None:
    config = {
        "client": {
            "base_url": "https://pokeapi.co/api/v2/",
        },
        "resource_defaults": {
            "endpoint": {
                "params": {
                    "limit": 1000,
                },
            }
        },
        "resources": [
            {
                "name": "pokemon_list",
                "endpoint": {
                    "path": "pokemon",
                    "paginator": SinglePagePaginator(),
                    "records_path": "results",
                    "params": {
                        "limit": 2,
                    },
                },
            },
            {
                "name": "pokemon",
                "endpoint": {
                    "path": "pokemon/{name}",
                    "params": {
                        "name": {
                            "type": "resolve",
                            "resource": "pokemon_list",
                            "field": "name",
                        },
                    },
                    "paginator": "single_page",
                },
            },
        ],
    }

    data = rest_api_source(config).with_resources("pokemon_list", "pokemon")
    pipeline = _make_pipeline(destination_name)
    load_info = pipeline.run(data)
    assert_load_info(load_info)
    table_names = [t["name"] for t in pipeline.default_schema.data_tables()]
    table_counts = load_table_counts(pipeline, *table_names)

    assert list(table_counts.keys()) == [
        "pokemon",
        "pokemon__types",
        "pokemon__stats",
        "pokemon__moves__version_group_details",
        "pokemon__moves",
        "pokemon__game_indices",
        "pokemon__forms",
        "pokemon__abilities",
        "pokemon_list",
    ]

    assert table_counts["pokemon_list"] == 2
    assert table_counts["pokemon"] == 2