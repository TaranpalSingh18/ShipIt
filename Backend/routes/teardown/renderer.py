from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from schemas.teardown import ProductTeardown

BASE_DIR = Path(__file__).parent

env = Environment(
    loader=FileSystemLoader(BASE_DIR / "template"),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


class TeardownRenderer:

    def __init__(self, template_name: str = "teardown.j2"):
        self.template = env.get_template(template_name)

    def render(self, teardown: ProductTeardown) -> str:
        return self.template.render(**teardown.model_dump())