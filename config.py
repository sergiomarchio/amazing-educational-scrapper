import yaml


class __Config:

    @property
    def config(self) -> dict:
        with open('config.yml', 'r') as f:
            return yaml.safe_load(f)


config = __Config().config
