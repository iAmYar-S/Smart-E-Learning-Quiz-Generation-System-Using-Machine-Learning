import google.generativeai as genai

# Paste your API key here
genai.configure(api_key="AIzaSyDPNM2glnzBP7jVGHnbaXV2CralBupW1zg")

print("Checking available models...")
try:
    # This asks Google directly: "What models am I allowed to use?"
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
            
    print("\nAttempting to connect to Gemini...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say hello world!")
    print("Success! AI says:", response.text)
    
except Exception as e:
    print("\nCRITICAL ERROR:", e)