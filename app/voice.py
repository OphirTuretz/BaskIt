import streamlit as st
import streamlit.components.v1 as components

def record_and_recognize():
    st.write("Click the button and speak to add an item:")
    st.info("After speaking, copy the recognized text below and paste it into the manual input field to add it to your list.")
    
    # Create a unique key for this component
    component_key = "voice_recognition"
    
    # HTML/JavaScript for speech recognition
    html_code = f"""
    <div style=\"text-align: center; padding: 20px;\">
        <button id=\"recordBtn\" onclick=\"startRecording()\" style=\"
            background-color: #ff4b4b; 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 25px; 
            font-size: 16px; 
            cursor: pointer;
            margin: 10px;\">
            🎤 Start Recording
        </button>
        
        <div id=\"status\" style=\"margin: 10px; font-weight: bold; color: #666;\"></div>
        <div id=\"result\" style=\"margin: 10px; padding: 10px; background-color: #f0f2f6; border-radius: 5px; min-height: 20px;\"></div>
        
        <input type=\"text\" id=\"voiceInput\" name=\"voiceInput\" value=\"\" style=\"width: 80%; margin-top: 10px;\" readonly placeholder=\"Recognized text will appear here. Copy it!\">
    </div>
    
    <script>
    let isRecording = false;
    let recognition;
    
    function startRecording() {{
        const btn = document.getElementById('recordBtn');
        const status = document.getElementById('status');
        const result = document.getElementById('result');
        const voiceInput = document.getElementById('voiceInput');
        
        if (!isRecording) {{
            // Start recording
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
                recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';
                
                recognition.onstart = function() {{
                    isRecording = true;
                    btn.innerHTML = '🛑 Stop Recording';
                    btn.style.backgroundColor = '#ff6b6b';
                    status.innerHTML = '🎤 Listening... Speak now!';
                    result.innerHTML = '';
                }};
                
                recognition.onresult = function(event) {{
                    const transcript = event.results[0][0].transcript;
                    result.innerHTML = '<strong>You said:</strong> ' + transcript;
                    status.innerHTML = '✅ Recognition complete!';
                    voiceInput.value = transcript;
                }};
                
                recognition.onerror = function(event) {{
                    status.innerHTML = '❌ Error: ' + event.error;
                    isRecording = false;
                    btn.innerHTML = '🎤 Start Recording';
                    btn.style.backgroundColor = '#ff4b4b';
                }};
                
                recognition.onend = function() {{
                    isRecording = false;
                    btn.innerHTML = '🎤 Start Recording';
                    btn.style.backgroundColor = '#ff4b4b';
                    if (status.innerHTML === '🎤 Listening... Speak now!') {{
                        status.innerHTML = '⏹️ Recording stopped';
                    }}
                }};
                
                recognition.start();
            }} else {{
                status.innerHTML = '❌ Speech recognition not supported in this browser';
            }}
        }} else {{
            // Stop recording
            recognition.stop();
        }}
    }}
    </script>
    """
    
    # Display the HTML component
    components.html(html_code, height=270)
    
    # Manual input fallback
    st.write("Paste the recognized text here (or type manually):")
    manual_input = st.text_input("Manual input", key="manual_voice_input")
    
    if manual_input:
        return manual_input
    
    return None 