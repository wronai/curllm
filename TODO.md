Create a new Python package directory 'curllm_core' and split curllm_server.py into reusable modules: config, logger, llm, vision, captcha, stealth, browserless, executor, server.
Update curllm_server.py to be a thin shim that runs the server from the new package.
Update pyproject.toml to include the new package.
Update examples.py to import the executor from the new package.
Add simple unit tests (Flask health endpoint and BQL parsing path). I'll create the new module files in parallel, then update existing files and add tests.


zaktualizuj changelog 
dodaj więcej testów
na bazie wskazówek z webtest/README.md stwórz nowy projekt webtest, uruchom, prztestuj z docker