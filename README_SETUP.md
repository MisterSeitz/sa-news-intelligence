# South African News Intelligence Actor

This Apify Actor scrapes South African news sites, extracts structured intelligence (people, crimes, locations) using AI, and ingests it into Supabase.

## Setup

1.  **Environment Variables**:
    You must set the following environment variables in your Apify Actor configuration or local `.env` file:
    *   `OPENAI_API_KEY`: Your OpenRouter or OpenAI API Key.
    *   `OPENAI_BASE_URL`: (Optional) `https://openrouter.ai/api/v1` if using OpenRouter.
    *   `SUPABASE_URL`: Your Visita Intelligence Supabase URL.
    *   `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase Service Role Key (for writing to DB).

2.  **Input Configuration**:
    The actor accepts the following input (optional):
    ```json
    {
        "test_mode": false
    }
    ```

3.  **Source List**:
    The actor reads sources from `reference_docs/news-sites/SA_NEWS_Intelligence.csv`. Ensure this file is included in your Actor build or accessible.

## Local Testing

To run locally with `test_mode=True` (mocking AI/DB):

1.  Set up a virtual environment:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    playwright install
    ```

2.  Run the actor:
    ```bash
    # Create a simple input file
    echo {"test_mode": true} > storage/key_value_stores/default/INPUT.json
    
    # Run
    apify run -p
    # OR directly
    python src/main.py
    ```
