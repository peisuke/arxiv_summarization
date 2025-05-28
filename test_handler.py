import pytest
import re
from unittest.mock import patch, MagicMock
from handler import (
    fetch_arxiv_info, 
    summarize, 
    handle_arxiv_request, 
    arxiv_pattern,
    Result
)


class TestArxivPattern:
    """Test the arXiv URL pattern matching"""
    
    def test_arxiv_pattern_basic_url(self):
        url = "https://arxiv.org/abs/2404.07979"
        match = re.search(arxiv_pattern, url)
        assert match is not None
        assert match.group(1) == "2404.07979"
    
    def test_arxiv_pattern_with_version(self):
        url = "https://arxiv.org/abs/2404.07979v1"
        match = re.search(arxiv_pattern, url)
        assert match is not None
        assert match.group(1) == "2404.07979"
    
    def test_arxiv_pattern_www_prefix(self):
        url = "https://www.arxiv.org/abs/2404.07979"
        match = re.search(arxiv_pattern, url)
        assert match is not None
        assert match.group(1) == "2404.07979"
    
    def test_arxiv_pattern_http(self):
        url = "http://arxiv.org/abs/2404.07979"
        match = re.search(arxiv_pattern, url)
        assert match is not None
        assert match.group(1) == "2404.07979"
    
    def test_arxiv_pattern_invalid_url(self):
        url = "https://google.com/abs/2404.07979"
        match = re.search(arxiv_pattern, url)
        assert match is None
    
    def test_arxiv_pattern_invalid_id_format(self):
        url = "https://arxiv.org/abs/invalid"
        match = re.search(arxiv_pattern, url)
        assert match is None


class TestFetchArxivInfo:
    """Test the arXiv API fetch functionality"""
    
    @patch('handler.requests.get')
    def test_fetch_arxiv_info_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <title>Test Paper Title</title>
        <summary>This is a test abstract for the paper.</summary>
    </entry>
</feed>'''
        mock_get.return_value = mock_response
        
        title, abstract = fetch_arxiv_info("2404.07979")
        
        assert title == "Test Paper Title"
        assert abstract == "This is a test abstract for the paper."
        mock_get.assert_called_once_with("http://export.arxiv.org/api/query?id_list=2404.07979")
    
    @patch('handler.requests.get')
    def test_fetch_arxiv_info_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        title, abstract = fetch_arxiv_info("invalid.id")
        
        assert title is None
        assert abstract is None
    
    @patch('handler.requests.get')
    def test_fetch_arxiv_info_empty_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>'''
        mock_get.return_value = mock_response
        
        title, abstract = fetch_arxiv_info("2404.07979")
        
        assert title == ""
        assert abstract == ""


class TestSummarize:
    """Test the OpenAI summarization functionality"""
    
    @patch('handler.oai_clinet.beta.chat.completions.parse')
    def test_summarize_success(self, mock_parse):
        mock_result = Result(
            problem="Test problem description",
            contribution="Test contribution description", 
            conclusion="Test conclusion description"
        )
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed = mock_result
        mock_parse.return_value = mock_response
        
        title = "Test Paper Title"
        abstract = "Test abstract content"
        
        result = summarize(title, abstract)
        
        expected = "*タイトル* :Test Paper Title\n*課題* ：Test problem description\n*貢献* :Test contribution description\n*結論* :Test conclusion description"
        assert result == expected
        
        mock_parse.assert_called_once()
        call_args = mock_parse.call_args
        assert call_args[1]['model'] == "gpt-4o"
        assert call_args[1]['response_format'] == Result
        assert len(call_args[1]['messages']) == 2
        assert "タイトル: Test Paper Title" in call_args[1]['messages'][1]['content']
        assert "概要: Test abstract content" in call_args[1]['messages'][1]['content']


class TestHandleArxivRequest:
    """Test the main request handling function"""
    
    @patch('handler.fetch_arxiv_info')
    @patch('handler.summarize')
    def test_handle_arxiv_request_success(self, mock_summarize, mock_fetch):
        mock_fetch.return_value = ("Test Title", "Test Abstract")
        mock_summarize.return_value = "Test Summary"
        
        text = "Check out this paper: https://arxiv.org/abs/2404.07979"
        result = handle_arxiv_request(text)
        
        assert result == "Test Summary"
        mock_fetch.assert_called_once_with("2404.07979")
        mock_summarize.assert_called_once_with("Test Title", "Test Abstract")
    
    @patch('handler.fetch_arxiv_info')
    def test_handle_arxiv_request_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = (None, None)
        
        text = "Check out this paper: https://arxiv.org/abs/2404.07979"
        result = handle_arxiv_request(text)
        
        assert result == "arXivから情報を取得できませんでした。"
    
    def test_handle_arxiv_request_no_url(self):
        text = "This text has no arXiv URL"
        result = handle_arxiv_request(text)
        
        expected = ("フォーマットが正しくありません。\n"
                   "`https://arxiv.org/abs/XXXX.XXXXX` という形式で送信してください。")
        assert result == expected
    
    def test_handle_arxiv_request_invalid_url(self):
        text = "Check out https://google.com instead"
        result = handle_arxiv_request(text)
        
        expected = ("フォーマットが正しくありません。\n"
                   "`https://arxiv.org/abs/XXXX.XXXXX` という形式で送信してください。")
        assert result == expected


class TestResultModel:
    """Test the Pydantic Result model"""
    
    def test_result_model_creation(self):
        result = Result(
            problem="Test problem",
            contribution="Test contribution",
            conclusion="Test conclusion"
        )
        
        assert result.problem == "Test problem"
        assert result.contribution == "Test contribution"
        assert result.conclusion == "Test conclusion"
    
    def test_result_model_validation(self):
        with pytest.raises(ValueError):
            Result(
                problem="Test problem",
                contribution="Test contribution"
                # Missing conclusion
            )