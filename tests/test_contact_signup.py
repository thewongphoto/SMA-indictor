"""Optional signup uses only the public HTTPS API and stable explicit request IDs."""
import os
from unittest import TestCase
from unittest.mock import Mock,patch
from sma_analyzer import contact

class ContactSignupTests(TestCase):
    def test_public_endpoint_is_https_and_override_can_disable_signup(self):
        with patch.dict(os.environ,{'SMA_CONTACT_BASE_URL':''}):self.assertEqual(contact.base_url(),'')
        with patch.dict(os.environ,{'SMA_CONTACT_BASE_URL':'http://example.com'}):self.assertEqual(contact.base_url(),'')
        with patch.dict(os.environ,{'SMA_CONTACT_BASE_URL':'https://example.com/'}):self.assertEqual(contact.base_url(),'https://example.com')

    def test_capability_requires_explicit_server_enablement(self):
        response=Mock();response.json.return_value={'enabled':False}
        with patch('requests.get',return_value=response) as get:
            self.assertFalse(contact.capabilities());get.assert_called_once()
        response.json.return_value={'enabled':True}
        with patch('requests.get',return_value=response):self.assertTrue(contact.capabilities())

    def test_email_submission_reuses_caller_ids_and_requires_service_acceptance(self):
        response=Mock(ok=True);response.json.return_value={'sent':True}
        with patch('requests.post',return_value=response) as post:
            result=contact.submit('person@example.com','installation','request')
            self.assertEqual(result,'person@example.com')
            payload=post.call_args.kwargs['json'];self.assertEqual(payload['request_id'],'request');self.assertEqual(payload['install_id'],'installation');self.assertEqual(payload['platform'],'android')
            self.assertTrue(post.call_args.args[0].startswith('https://'))
        response.json.return_value={'sent':False}
        with patch('requests.post',return_value=response),self.assertRaises(contact.ContactError):contact.submit('person@example.com')

    def test_expired_intent_error_is_available_for_explicit_retry(self):
        response=Mock(ok=False);response.json.return_value={'error':'Please retry this expired request.','code':'expired'}
        with patch('requests.post',return_value=response),self.assertRaises(contact.ContactError) as result:contact.submit('person@example.com')
        self.assertEqual(result.exception.code,'expired')

    def test_remove_sends_an_explicit_operation_and_the_same_installation_identity(self):
        response=Mock(ok=True);response.json.return_value={'sent':True,'change':'remove'}
        with patch('requests.post',return_value=response) as post:
            contact.submit('person@example.com','installation','request','remove')
            payload=post.call_args.kwargs['json']
            self.assertEqual(payload['operation'],'remove')
            self.assertEqual(payload['install_id'],'installation')
            self.assertEqual(payload['request_id'],'request')
            self.assertEqual(payload['platform'],'android')

    def test_unknown_operation_does_not_send(self):
        with patch('requests.post') as post,self.assertRaises(ValueError):
            contact.submit('person@example.com',operation='clear-everyone')
        post.assert_not_called()

    def test_invalid_address_never_makes_a_network_request(self):
        with patch('requests.post') as post:
            for email in ('','not-an-email','person@example.com\nBcc: other@example.com'):
                with self.assertRaises(ValueError):contact.submit(email)
            post.assert_not_called()
