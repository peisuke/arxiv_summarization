from src.arxiv_slack_bot.handler import handle_arxiv_request


if __name__ == "__main__":
    test_text = "https://arxiv.org/abs/2404.07979"
    first_post, second_post = handle_arxiv_request(test_text)

    print("\n--- 要約結果（分割版） ---\n")
    print("=== 1つ目の投稿 ===")
    print(first_post)
    print("\n=== 2つ目の投稿 ===")
    print(second_post)