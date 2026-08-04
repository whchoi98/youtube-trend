from fastapi import Request


def get_settings(request: Request):
    return request.app.state.settings


def get_store(request: Request):
    return request.app.state.store


def get_yt(request: Request):
    return request.app.state.yt


def get_llm(request: Request):
    return request.app.state.llm
