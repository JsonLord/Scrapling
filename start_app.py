from scrapling.core.ai import ScraplingMCPServer

if __name__ == "__main__":
    server = ScraplingMCPServer()
    server.serve(http=True, host="0.0.0.0", port=7860)
