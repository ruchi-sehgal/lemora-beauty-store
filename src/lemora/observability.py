import logfire


def setup():
    # Sends nothing unless LOGFIRE_TOKEN is set, so tests and CI stay quiet.
    logfire.configure(send_to_logfire="if-token-present", service_name="lemora")
    logfire.instrument_pydantic_ai()