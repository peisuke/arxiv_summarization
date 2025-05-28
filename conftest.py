import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Mock environment variables for all tests"""
    env_vars = {
        'SLACK_SIGNING_SECRET': 'test_slack_signing_secret',
        'SLACK_BOT_TOKEN': 'xoxb-test-slack-bot-token',
        'OPENAI_API_KEY': 'sk-test-openai-api-key'
    }
    
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def sample_arxiv_xml():
    """Sample arXiv API XML response for testing"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <title>Attention Is All You Need</title>
        <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.</summary>
    </entry>
</feed>'''


@pytest.fixture
def sample_slack_event():
    """Sample Slack event payload for testing"""
    return {
        "event": {
            "type": "app_mention",
            "channel": "C1234567890",
            "text": "<@U123456789> https://arxiv.org/abs/1706.03762",
            "ts": "1234567890.123456",
            "user": "U123456789"
        },
        "type": "event_callback",
        "team_id": "T1234567890",
        "api_app_id": "A1234567890"
    }


@pytest.fixture
def sample_openai_response():
    """Sample OpenAI API response structure"""
    from handler import Result
    return Result(
        problem="既存のシーケンス変換モデルは複雑なRNNやCNNに依存しており、並列化が困難で計算効率が悪いという課題がある。",
        contribution="注意機構のみに基づく新しいTransformerアーキテクチャを提案し、RNNやCNNを完全に排除することで、並列化可能で効率的なモデルを実現した。",
        conclusion="Transformerは翻訳タスクにおいて既存モデルを上回る性能を示し、訓練時間も大幅に短縮された。注意機構のみでシーケンス変換が可能であることを実証した。"
    )