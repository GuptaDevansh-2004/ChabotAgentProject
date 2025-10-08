class LLMConfig:
    """Provides configuration parameters for LLM Model"""

    MODEL = "gemini-2.5-flash"

    # LLM model (Gemini) configuration parameters
    TOP_K = 40
    TOP_P = 0.95
    TEMPERATURE = 0.7
    MAX_OUTPUT_TOKENS = 20000
    RESPONSE_TYPE = "application/json"

    # contents configuration for LLM model (Gemini)
    MAX_HISTORY = 20