import unittest
from unittest.mock import patch
import requests
from orchestrator.gateway import LLMGateway

class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        self.gateway = LLMGateway()

    @patch('requests.post')
    def test_ollama_timeout(self, mock_post):
        # Simulate a timeout
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with self.assertRaises(RuntimeError) as cm:
            self.gateway._get_ollama_response("test", "test")
        
        self.assertIn("timed out", str(cm.exception))

    @patch('requests.post')
    def test_ollama_connection_error(self, mock_post):
        # Simulate a connection error
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        with self.assertRaises(RuntimeError) as cm:
            self.gateway._get_ollama_response("test", "test")
        
        self.assertIn("Cannot connect to Ollama", str(cm.exception))

    @patch('requests.post')
    def test_ollama_api_error(self, mock_post):
        # Simulate a general request error
        mock_post.side_effect = requests.exceptions.RequestException("Generic Error")
        
        with self.assertRaises(RuntimeError) as cm:
            self.gateway._get_ollama_response("test", "test")
        
        self.assertIn("Ollama API Error", str(cm.exception))

class TestOrchestratorErrors(unittest.TestCase):
    def setUp(self):
        self.orchestrator = Orchestrator()

    @patch('orchestrator.gateway.LLMGateway.get_response')
    def test_orchestrator_error_propagation(self, mock_get_response):
        # Simulate an exception in the gateway
        mock_get_response.side_effect = RuntimeError("Something went wrong")
        
        response = self.orchestrator.process_command("test")
        
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['message'], "Something went wrong")

if __name__ == '__main__':
    from orchestrator.brain import Orchestrator
    unittest.main()
