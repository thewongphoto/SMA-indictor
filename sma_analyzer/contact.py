"""Optional release-update signup, separate from retired alert email delivery."""
import os
import uuid
from .notifications import validate_email

# Public service address only. Configure before packaging; never embed credentials.
CONTACT_BASE_URL = ''

def base_url():
    value=os.environ.get('SMA_CONTACT_BASE_URL',CONTACT_BASE_URL).rstrip('/')
    return value if value.startswith('https://') else ''

def capabilities():
    if not base_url(): return False
    import requests
    response=requests.get(base_url()+'/api/contact-capabilities',timeout=10)
    response.raise_for_status()
    return response.json().get('enabled') is True

def submit(email, install_id=None):
    email=email.strip()
    if not validate_email(email): raise ValueError('Enter a valid email address, like name@example.com.')
    if not base_url(): raise ValueError('Release update signup is not configured.')
    import requests
    from .version import APP_VERSION
    response=requests.post(base_url()+'/api/contact-email',json={'email':email,
        'install_id':install_id or str(uuid.uuid4()),'platform':'android','version':APP_VERSION},timeout=15)
    response.raise_for_status()
    if response.json().get('sent') is not True: raise ValueError('The email service has not confirmed delivery.')
    return email
