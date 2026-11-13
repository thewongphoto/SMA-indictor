"""Optional release-update signup, separate from retired market-alert email."""
import os
import uuid
from .notifications import validate_email

# Public service address only. Delivery credentials stay on Vercel.
CONTACT_BASE_URL = 'https://sma-indictor-xyx2.vercel.app'

class ContactError(ValueError):
    def __init__(self,message,code=''):
        super().__init__(message)
        self.code=code

def base_url():
    value=os.environ.get('SMA_CONTACT_BASE_URL',CONTACT_BASE_URL).rstrip('/')
    return value if value.startswith('https://') else ''

def capabilities():
    if not base_url(): return False
    import requests
    response=requests.get(base_url()+'/api/contact-capabilities',timeout=10)
    response.raise_for_status()
    return response.json().get('enabled') is True

def submit(email, install_id=None, request_id=None):
    email=validate_email(email)
    if not email: raise ContactError('Enter a valid email address, like name@example.com.')
    if not base_url(): raise ContactError('Release update signup is not configured.')
    import requests
    from .version import APP_VERSION
    response=requests.post(base_url()+'/api/contact-email',json={'email':email,
        'install_id':install_id or str(uuid.uuid4()),'request_id':request_id or str(uuid.uuid4()),
        'platform':'android','version':APP_VERSION},timeout=25)
    try:result=response.json()
    except ValueError:raise ContactError('Email acceptance could not be confirmed. Try again later.') from None
    if not response.ok or result.get('sent') is not True:
        raise ContactError(result.get('error') or 'Email acceptance could not be confirmed. Try again later.',result.get('code',''))
    return email
