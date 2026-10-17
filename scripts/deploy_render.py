"""Request deployment of the exact tested commit without logging hook credentials."""
import json
import os
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def deployment_url(hook, commit):
    parts = urlsplit(hook)
    if parts.scheme != 'https' or parts.hostname != 'api.render.com' or not parts.path.startswith('/deploy/'):
        raise ValueError('Set RENDER_DEPLOY_HOOK_URL to the deploy hook from Render service settings.')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('GITHUB_SHA must be a full commit SHA.')
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != 'ref']
    query.append(('ref', commit))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))


def main():
    try:
        hook = os.environ.get('RENDER_DEPLOY_HOOK_URL', '')
        if not hook:
            raise ValueError('Add the RENDER_DEPLOY_HOOK_URL GitHub Actions repository secret.')
        url = deployment_url(hook, os.environ.get('GITHUB_SHA', ''))
        with urlopen(Request(url, method='POST'), timeout=30) as response:
            if response.status not in (200, 202):
                raise RuntimeError('Deploy request was rejected')
            payload = json.load(response)
        deploy_id = payload.get('deploy', {}).get('id')
        print('Render accepted the deployment request.' + (f' Deployment ID: {deploy_id}' if deploy_id else ' Deployment queued.'))
        print('This confirms acceptance, not a successful rollout. Check the Render dashboard for the live result.')
    except Exception:
        print('Deployment request failed. Verify the hook secret, linked repository, branch, and Render service status.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
