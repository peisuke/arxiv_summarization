import pytest
import json
import time
import hmac
import hashlib
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from main import app, verify_slack_request


class TestVerifySlackRequest:
    """Test Slack request verification functionality"""
    
    def test_verify_slack_request_valid(self):
        # Setup
        signing_secret = "test_secret"
        timestamp = str(int(time.time()))
        body = "test_body"
        
        # Create valid signature
        sig_basestring = f"v0:{timestamp}:{body}".encode("utf-8")
        computed_signature = "v0=" + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": computed_signature
        }
        
        with patch('main.SLACK_SIGNING_SECRET', signing_secret):
            result = verify_slack_request(headers, body)
            assert result is True
    
    def test_verify_slack_request_missing_timestamp(self):
        headers = {
            "x-slack-signature": "v0=test_signature"
        }
        result = verify_slack_request(headers, "test_body")
        assert result is False
    
    def test_verify_slack_request_missing_signature(self):
        headers = {
            "x-slack-request-timestamp": str(int(time.time()))
        }
        result = verify_slack_request(headers, "test_body")
        assert result is False
    
    def test_verify_slack_request_expired_timestamp(self):
        # Timestamp older than 5 minutes
        old_timestamp = str(int(time.time()) - 400)
        headers = {
            "x-slack-request-timestamp": old_timestamp,
            "x-slack-signature": "v0=test_signature"
        }
        result = verify_slack_request(headers, "test_body")
        assert result is False
    
    def test_verify_slack_request_invalid_signature(self):
        timestamp = str(int(time.time()))
        headers = {
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": "v0=invalid_signature"
        }
        
        with patch('main.SLACK_SIGNING_SECRET', "test_secret"):
            result = verify_slack_request(headers, "test_body")
            assert result is False


class TestSlackWebhook:
    """Test the main Slack webhook endpoint"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    @patch('main.verify_slack_request')
    def test_unauthorized_request(self, mock_verify):
        mock_verify.return_value = False
        
        response = self.client.post("/", content="test_body")
        
        assert response.status_code == 401
        assert response.json() == {"error": "unauthorized"}
    
    @patch('main.verify_slack_request')
    def test_url_verification_challenge(self, mock_verify):
        mock_verify.return_value = True
        
        challenge_payload = {
            "type": "url_verification",
            "challenge": "test_challenge_token"
        }
        
        response = self.client.post("/", json=challenge_payload)
        
        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge_token"}
    
    @patch('main.verify_slack_request')
    def test_retry_request_ignored(self, mock_verify):
        mock_verify.return_value = True
        
        headers = {"x-slack-retry-num": "1"}
        response = self.client.post("/", json={}, headers=headers)
        
        assert response.status_code == 200
        assert response.json() == {"message": "Retry ignored"}
    
    @patch('main.verify_slack_request')
    def test_non_app_mention_event(self, mock_verify):
        mock_verify.return_value = True
        
        event_payload = {
            "event": {
                "type": "message",
                "text": "regular message"
            }
        }
        
        response = self.client.post("/", json=event_payload)
        
        assert response.status_code == 200
        assert response.json() == {"message": "No action taken"}
    
    @patch('main.verify_slack_request')
    def test_missing_event(self, mock_verify):
        mock_verify.return_value = True
        
        payload = {"not_event": "data"}
        
        response = self.client.post("/", json=payload)
        
        assert response.status_code == 200
        assert response.json() == {"message": "No action taken"}
    
    @patch('main.client.chat_postMessage')
    @patch('main.handle_arxiv_request')
    @patch('main.verify_slack_request')
    def test_successful_app_mention(self, mock_verify, mock_handle, mock_post_message):
        mock_verify.return_value = True
        mock_handle.return_value = "Test response from handler"
        mock_post_message.return_value = None
        
        event_payload = {
            "event": {
                "type": "app_mention",
                "channel": "C1234567890",
                "text": "<@U123456789> https://arxiv.org/abs/2404.07979",
                "ts": "1234567890.123456"
            }
        }
        
        response = self.client.post("/", json=event_payload)
        
        assert response.status_code == 200
        assert response.json() == {"message": "Processed"}
        
        mock_handle.assert_called_once_with("<@U123456789> https://arxiv.org/abs/2404.07979")
        mock_post_message.assert_called_once_with(
            channel="C1234567890",
            text="Test response from handler",
            thread_ts="1234567890.123456",
            reply_broadcast=True
        )
    
    @patch('main.client.chat_postMessage')
    @patch('main.handle_arxiv_request')
    @patch('main.verify_slack_request')
    def test_slack_api_error_handling(self, mock_verify, mock_handle, mock_post_message):
        from slack_sdk.errors import SlackApiError
        
        mock_verify.return_value = True
        mock_handle.return_value = "Test response"
        mock_post_message.side_effect = SlackApiError("API Error", response=MagicMock())
        
        event_payload = {
            "event": {
                "type": "app_mention",
                "channel": "C1234567890",
                "text": "test message",
                "ts": "1234567890.123456"
            }
        }
        
        # Should not raise exception and return success
        response = self.client.post("/", json=event_payload)
        
        assert response.status_code == 200
        assert response.json() == {"message": "Processed"}
    
    @patch('main.client.chat_postMessage')
    @patch('main.handle_arxiv_request')
    @patch('main.verify_slack_request')
    def test_app_mention_without_text(self, mock_verify, mock_handle, mock_post_message):
        mock_verify.return_value = True
        mock_handle.return_value = "Handler response"
        mock_post_message.return_value = None
        
        event_payload = {
            "event": {
                "type": "app_mention",
                "channel": "C1234567890",
                "ts": "1234567890.123456"
                # No "text" field
            }
        }
        
        response = self.client.post("/", json=event_payload)
        
        assert response.status_code == 200
        assert response.json() == {"message": "Processed"}
        
        # Should pass empty string when text is missing
        mock_handle.assert_called_once_with("")


class TestAppConfiguration:
    """Test application configuration and setup"""
    
    @patch.dict('os.environ', {
        'SLACK_SIGNING_SECRET': 'test_secret',
        'SLACK_BOT_TOKEN': 'test_token'
    })
    def test_environment_variables_loaded(self):
        # Reload main module to test environment variable loading
        import importlib
        import main
        importlib.reload(main)
        
        assert main.SLACK_SIGNING_SECRET == 'test_secret'
        assert main.SLACK_BOT_TOKEN == 'test_token'
    
    def test_fastapi_app_creation(self):
        assert app is not None
        assert hasattr(app, 'post')


class TestIntegration:
    """Integration tests combining multiple components"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    @patch('main.handle_arxiv_request')
    @patch('main.client.chat_postMessage')
    def test_full_workflow_with_valid_arxiv_url(self, mock_post_message, mock_handle):
        mock_handle.return_value = "Successfully processed arXiv paper"
        mock_post_message.return_value = None
        
        # Create valid request
        timestamp = str(int(time.time()))
        body_data = {
            "event": {
                "type": "app_mention",
                "channel": "C1234567890",
                "text": "<@U123456789> https://arxiv.org/abs/2404.07979",
                "ts": "1234567890.123456"
            }
        }
        body = json.dumps(body_data)
        
        # Create valid signature
        with patch('main.SLACK_SIGNING_SECRET', 'test_secret'):
            sig_basestring = f"v0:{timestamp}:{body}".encode("utf-8")
            computed_signature = "v0=" + hmac.new(
                'test_secret'.encode("utf-8"),
                sig_basestring,
                hashlib.sha256
            ).hexdigest()
        
            headers = {
                "x-slack-request-timestamp": timestamp,
                "x-slack-signature": computed_signature,
                "content-type": "application/json"
            }
        
            response = self.client.post("/", content=body, headers=headers)
        
            assert response.status_code == 200
            assert response.json() == {"message": "Processed"}
            mock_handle.assert_called_once()
            mock_post_message.assert_called_once()