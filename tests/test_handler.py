from src.arxiv_slack_bot.handler import handle_arxiv_request


if __name__ == "__main__":
    test_text = "https://arxiv.org/abs/2404.07979"
    result = handle_arxiv_request(test_text)

    print("\n--- 要約結果 ---\n")
    print(result)