import json


def fig_to_dict(fig) -> dict:
    return json.loads(fig.to_json())
