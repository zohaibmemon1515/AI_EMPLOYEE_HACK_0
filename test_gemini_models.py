#!/usr/bin/env python3
"""Test script to list available Gemini models."""

import os
import google.generativeai as genai

# Configure with your API key
api_key = ""
genai.configure(api_key=api_key)

print("=" * 60)
print("Available Gemini Models")
print("=" * 60)

try:
    # List all available models
    models = genai.list_models()
    
    for model in models:
        # Check if model supports generateContent
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✅ {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Methods: {model.supported_generation_methods}")
    
    print("\n" + "=" * 60)
    print("Recommended models for text generation:")
    print("=" * 60)
    
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            if 'flash' in model.name.lower():
                print(f"   • {model.name} (Fast, recommended)")
            elif 'pro' in model.name.lower():
                print(f"   • {model.name} (Balanced)")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nTry these model names manually:")
    print("   • gemini-1.0-pro")
    print("   • gemini-1.5-flash-latest")
    print("   • gemini-1.5-pro-latest")
