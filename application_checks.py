"""Small application scenarios run with an isolated wheel directory."""

import json
import sys
import traceback


def django_template():
    from django.conf import settings
    from django.template import Context, Engine

    settings.configure(USE_I18N=False)
    template = Engine().from_string("{% for item in items %}{{ item }}{% if not forloop.last %}, {% endif %}{% endfor %}")
    rendered = template.render(Context({"items": ["<draft>", "ready"]}))
    assert rendered == "&lt;draft&gt;, ready", rendered


def django_sqlite():
    import django
    from django.conf import settings

    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[],
        USE_TZ=True,
    )
    django.setup()
    from django.db import connection, models, transaction

    class Item(models.Model):
        label = models.CharField(max_length=20)
        quantity = models.IntegerField()

        class Meta:
            app_label = "dashboard_checks"

    with connection.schema_editor() as schema:
        schema.create_model(Item)
    Item.objects.bulk_create([Item(label="red", quantity=3), Item(label="blue", quantity=4)])
    with transaction.atomic():
        Item.objects.create(label="draft", quantity=50)
        transaction.set_rollback(True)
    observed = Item.objects.filter(quantity__gte=3).aggregate(total=models.Sum("quantity"))
    assert observed == {"total": 7}, observed


def bottle_route():
    from wsgiref.util import setup_testing_defaults

    from bottle import Bottle, request

    app = Bottle()

    @app.get("/items/<identifier:int>")
    def item(identifier):
        return {"id": identifier, "preview": request.query.preview == "yes"}

    environ = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO="/items/42", QUERY_STRING="preview=yes")

    def check_headers(status, headers, exc_info=None):
        assert status.startswith("200 "), status
        assert dict(headers)["Content-Type"].startswith("application/json"), headers

    payload = b"".join(app(environ, check_headers))
    assert json.loads(payload) == {"id": 42, "preview": True}, payload


def numpy_array():
    import os

    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    import numpy as np

    source = np.arange(12, dtype=np.int64).reshape(3, 4)
    assert (source[:, ::-2] + [1, 2]).sum(axis=0).tolist() == [24, 21]
    coefficients = np.array([[3.0, 1.0], [1.0, 2.0]])
    solution = np.linalg.solve(coefficients, [7.0, 4.0])
    assert np.allclose(solution, [2.0, 1.0], rtol=1e-12, atol=1e-12), solution


CHECKS = {
    "django-template": django_template,
    "django-sqlite": django_sqlite,
    "bottle-route": bottle_route,
    "numpy-array": numpy_array,
}


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[2])
    try:
        CHECKS[sys.argv[1]]()
    except Exception:
        # The end of the traceback, with the wheel directory shortened.
        lines = traceback.format_exc().replace(sys.argv[2], "<wheels>").strip().splitlines()
        outcome = {"status": "error", "detail": "\n".join(lines[-15:])}
    else:
        outcome = {"status": "passed", "detail": ""}
    print(json.dumps(outcome))
