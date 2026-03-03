import os
import time
from pathlib import Path
import pytest

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

ARTIFACTS_DIR = Path(__file__).parent / 'artifacts'
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # standard hook to expose test outcome on the item for fixtures
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    return rep


@pytest.fixture(autouse=True)
def trace_on_failure(page, request):
    """Starts Playwright tracing for each test and saves artifacts if the test fails."""
    context = page.context
    console_messages = []

    def _on_console(msg):
        try:
            console_messages.append(msg.text())
        except Exception:
            console_messages.append(str(msg))

    page.on('console', _on_console)

    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    except Exception:
        # Not critical, continue without tracing
        pass

    yield

    # After test
    failed = getattr(request.node, 'rep_call', None) and request.node.rep_call.failed
    ts = int(time.time())
    safe_name = request.node.name.replace('/', '_').replace(':', '_')
    base = ARTIFACTS_DIR / f"{safe_name}-{ts}"

    try:
        if failed:
            # Save Playwright trace
            trace_path = f"{base}.zip"
            try:
                context.tracing.stop(path=str(trace_path))
            except Exception:
                pass

            # Save screenshot
            try:
                ss_path = f"{base}.png"
                page.screenshot(path=ss_path, full_page=True)
            except Exception:
                pass

            # Save page HTML
            try:
                html_path = f"{base}.html"
                with open(html_path, 'w', encoding='utf-8') as fh:
                    fh.write(page.content())
            except Exception:
                pass

            # Save console messages
            try:
                cm_path = f"{base}-console.log"
                with open(cm_path, 'w', encoding='utf-8') as fh:
                    for m in console_messages:
                        fh.write(m + '\n')
            except Exception:
                pass
        else:
            # Stop tracing quietly to avoid leaving context tracing running
            try:
                context.tracing.stop()
            except Exception:
                pass
    except Exception:
        # Don't fail the test teardown because of artifact collection
        pass


@pytest.fixture
def e2e_roles_data(django_db_blocker):
    """Create a company, admin user and a role for e2e role tests and return sessionid."""
    with django_db_blocker.unblock():
        from django.test import Client
        from django.contrib.auth import get_user_model
        from empresas.models import Empresa, Role

        User = get_user_model()

        empresa = Empresa.objects.create(nome='E2E Empresa Roles')
        user = User.objects.create_user(username='e2eadmin', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        # Create a role for testing
        role = Role.objects.create(empresa=empresa, name='E2E Role')

        client = Client()
        assert client.login(username='e2eadmin', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'role': role, 'sessionid': sessionid}
