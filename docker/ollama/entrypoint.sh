#!/bin/bash

# Start the Ollama server in the background
ollama serve &
pid=$!

echo "Waiting for Ollama server to start..."
# Wait for the server to be responsive
until ollama list > /dev/null 2>&1; do
  sleep 1
done

# Pull the model if it's specified and not already present
if [ -n "$OLLAMA_MODEL" ]; then
    echo "Checking for model: $OLLAMA_MODEL"
    if ! ollama list | grep -q "$OLLAMA_MODEL"; then
        echo "Pulling model: $OLLAMA_MODEL"
        ollama pull "$OLLAMA_MODEL"
    else
        echo "Model $OLLAMA_MODEL already exists."
    fi
else
    echo "OLLAMA_MODEL environment variable not set. Skipping pull."
fi

# Bring the server process back to the foreground
wait $pid
