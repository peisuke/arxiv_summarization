import pytest
from unittest.mock import patch, MagicMock
from handler import handle_arxiv_request, fetch_arxiv_info, Result


class TestEndToEndIntegration:
    """End-to-end integration tests that simulate real workflows"""
    
    @patch('handler.oai_clinet.beta.chat.completions.parse')
    @patch('handler.requests.get')
    def test_complete_arxiv_processing_flow(self, mock_requests, mock_openai):
        """Test the complete flow from arXiv URL to summary"""
        
        # Mock arXiv API response
        mock_arxiv_response = MagicMock()
        mock_arxiv_response.status_code = 200
        mock_arxiv_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <title>Attention Is All You Need</title>
        <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.</summary>
    </entry>
</feed>'''
        mock_requests.return_value = mock_arxiv_response
        
        # Mock OpenAI response
        mock_result = Result(
            problem="既存のシーケンス変換モデルは複雑なRNNやCNNに依存しており、並列化が困難で計算効率が悪いという課題がある。",
            contribution="注意機構のみに基づく新しいTransformerアーキテクチャを提案し、RNNやCNNを完全に排除することで、並列化可能で効率的なモデルを実現した。",
            conclusion="Transformerは翻訳タスクにおいて既存モデルを上回る性能を示し、訓練時間も大幅に短縮された。注意機構のみでシーケンス変換が可能であることを実証した。"
        )
        mock_openai_response = MagicMock()
        mock_openai_response.choices[0].message.parsed = mock_result
        mock_openai.return_value = mock_openai_response
        
        # Test the complete flow
        text = "Please summarize: https://arxiv.org/abs/1706.03762"
        result = handle_arxiv_request(text)
        
        # Verify the result format
        assert "*タイトル* :Attention Is All You Need" in result
        assert "*課題* ：既存のシーケンス変換モデルは複雑な" in result
        assert "*貢献* :注意機構のみに基づく新しい" in result
        assert "*結論* :Transformerは翻訳タスクにおいて" in result
        
        # Verify API calls
        mock_requests.assert_called_once_with("http://export.arxiv.org/api/query?id_list=1706.03762")
        mock_openai.assert_called_once()
    
    @patch('handler.requests.get')
    def test_arxiv_api_failure_handling(self, mock_requests):
        """Test handling of arXiv API failures"""
        
        # Mock failed arXiv API response
        mock_arxiv_response = MagicMock()
        mock_arxiv_response.status_code = 404
        mock_requests.return_value = mock_arxiv_response
        
        text = "Please summarize: https://arxiv.org/abs/9999.99999"
        result = handle_arxiv_request(text)
        
        assert result == "arXivから情報を取得できませんでした。"
    
    def test_invalid_url_formats(self):
        """Test various invalid URL formats"""
        
        test_cases = [
            "No URL here",
            "https://google.com/search?q=test",
            "arxiv.org/abs/1234.5678",  # Missing protocol
            "https://arxiv.org/abs/invalid-format",
            "https://arxiv.org/paper/1234.5678",  # Wrong path
        ]
        
        expected_error = ("フォーマットが正しくありません。\n"
                         "`https://arxiv.org/abs/XXXX.XXXXX` という形式で送信してください。")
        
        for test_text in test_cases:
            result = handle_arxiv_request(test_text)
            assert result == expected_error
    
    def test_url_extraction_from_various_contexts(self):
        """Test URL extraction from different text contexts"""
        
        valid_contexts = [
            "Check this out: https://arxiv.org/abs/2404.07979",
            "https://arxiv.org/abs/2404.07979 looks interesting",
            "Paper at https://arxiv.org/abs/2404.07979v1 is good",
            "See: https://www.arxiv.org/abs/2404.07979",
            "HTTP link: http://arxiv.org/abs/2404.07979",
            "Multiple links: https://google.com and https://arxiv.org/abs/2404.07979",
        ]
        
        with patch('handler.fetch_arxiv_info') as mock_fetch:
            mock_fetch.return_value = (None, None)  # Simulate fetch failure
            
            for context in valid_contexts:
                result = handle_arxiv_request(context)
                # Should attempt to fetch, not return format error
                assert result == "arXivから情報を取得できませんでした。"
                mock_fetch.assert_called_with("2404.07979")
                mock_fetch.reset_mock()


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('handler.oai_clinet.beta.chat.completions.parse')
    def test_openai_api_error(self, mock_openai):
        """Test handling of OpenAI API errors"""
        
        # Mock OpenAI API failure
        mock_openai.side_effect = Exception("API Error")
        
        with patch('handler.fetch_arxiv_info') as mock_fetch:
            mock_fetch.return_value = ("Test Title", "Test Abstract")
            
            # Should raise the exception
            with pytest.raises(Exception):
                handle_arxiv_request("https://arxiv.org/abs/2404.07979")
    
    @patch('handler.requests.get')
    def test_malformed_xml_response(self, mock_requests):
        """Test handling of malformed XML from arXiv API"""
        
        # Mock malformed XML response
        mock_arxiv_response = MagicMock()
        mock_arxiv_response.status_code = 200
        mock_arxiv_response.text = "Invalid XML content"
        mock_requests.return_value = mock_arxiv_response
        
        title, abstract = fetch_arxiv_info("2404.07979")
        
        # Should handle XML parsing error gracefully
        assert title == ""
        assert abstract == ""


class TestPerformance:
    """Performance and edge case tests"""
    
    def test_very_long_text_with_url(self):
        """Test handling of very long text containing arXiv URL"""
        
        long_text = "Lorem ipsum " * 1000 + " https://arxiv.org/abs/2404.07979 " + "dolor sit amet " * 1000
        
        with patch('handler.fetch_arxiv_info') as mock_fetch:
            mock_fetch.return_value = (None, None)
            
            result = handle_arxiv_request(long_text)
            assert result == "arXivから情報を取得できませんでした。"
            mock_fetch.assert_called_once_with("2404.07979")
    
    def test_multiple_arxiv_urls(self):
        """Test text with multiple arXiv URLs (should process first one)"""
        
        text = "First: https://arxiv.org/abs/2404.07979 Second: https://arxiv.org/abs/1706.03762"
        
        with patch('handler.fetch_arxiv_info') as mock_fetch:
            mock_fetch.return_value = (None, None)
            
            result = handle_arxiv_request(text)
            # Should process the first URL found
            mock_fetch.assert_called_once_with("2404.07979")