import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";

const QAPage = () => {
  const { id: docId } = useParams();
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState({ initial: true, qa: false });
  const [fileInfo, setFileInfo] = useState(null);
  const [error, setError] = useState("");
  const chatEndRef = useRef(null);
  // Load initial file info
  useEffect(() => {
    const loadFileInfo = async () => {
      try {
        // Check localStorage first
        const savedFiles = localStorage.getItem('uploadedFiles');
        if (savedFiles) {
          const files = JSON.parse(savedFiles);
          const currentFile = files.find(f => f.file_id === docId);
          if (currentFile) {
            setFileInfo({
              name: currentFile.filename,
              uploaded: new Date(currentFile.created_at).toLocaleDateString()
            });
            setLoading(prev => ({ ...prev, initial: false }));
            return;
          }
        }

        // Fallback to API if not in localStorage
        const { data } = await axios.get(`http://localhost:8000/api/file-info/${docId}`);
        setFileInfo({
          name: data.filename,
          uploaded: new Date(data.upload_date).toLocaleDateString()
        });
        setLoading(prev => ({ ...prev, initial: false }));
      } catch (err) {
        setError("Failed to load document info");
        setLoading(prev => ({ ...prev, initial: false }));
      }
    };
    loadFileInfo();
  }, [docId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading.qa) return;

    setLoading(prev => ({ ...prev, qa: true }));
    setError("");
    
    try {
      // Add user question
      const userMessage = {
        type: "user",
        text: question,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMessage]);

      // Get API response
      const { data } = await axios.post(
        `http://localhost:8000/api/qa/${docId}`,
        { question }
      );

      // Add bot response
      const botMessage = {
        type: "bot",
        text: data.answer,
        sources: data.sources,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to get answer");
    } finally {
      setQuestion("");
      setLoading(prev => ({ ...prev, qa: false }));
    }
  };
  if (loading.initial) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center p-8">
      <div className="max-w-4xl w-full">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Document Q/A</h1>
          <button
            onClick={() => navigate(-1)}
            className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-md flex items-center gap-2 border border-gray-600"
          >
            <span>&larr;</span> Back to Files
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 p-4 rounded-lg mb-6 border border-red-500">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {fileInfo && (
          <div className="bg-gray-900 p-4 rounded-lg mb-6 grid grid-cols-2 gap-4 border border-gray-700">
            <div>
              <p className="text-gray-400 text-sm">Filename</p>
              <p className="truncate">{fileInfo.name}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Upload Date</p>
              <p>{fileInfo.uploaded}</p>
            </div>
          </div>
        )}

        <div className="bg-gray-900 p-6 rounded-lg shadow-xl border border-gray-700">
          <div className="h-[500px] overflow-y-auto bg-gray-900 p-4 rounded-lg mb-6 border border-gray-700">
            {messages.map((msg, index) => (
              <div key={index} className={`mb-6 ${msg.type === "user" ? "text-right" : "text-left"}`}>
                <div className={`inline-block max-w-[85%] p-4 rounded-lg border ${
                  msg.type === "user" 
                    ? "bg-blue-600 border-blue-500" 
                    : "bg-gray-800 border-gray-600"
                }`}>
                  <p className="text-sm text-gray-300 mb-2">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                  <p className="text-gray-100 mb-2">{msg.text}</p>
                  {msg.sources && (
                    <div className="mt-2 pt-2 border-t border-gray-500">
                      <p className="text-xs text-gray-400 mb-1">Sources:</p>
                      {msg.sources.map((source, i) => (
                        <p key={i} className="text-xs text-gray-400 truncate">
                          {source}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={handleAsk} className="flex gap-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about the document..."
              className="bg-gray-900 text-white px-4 py-3 rounded-lg flex-grow focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-700"
              disabled={loading.qa}
            />
            <button
              type="submit"
              disabled={!question.trim() || loading.qa}
              className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading.qa ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <>
                  <span>&rarr;</span>
                  Ask
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default QAPage;