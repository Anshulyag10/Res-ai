import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import UploadPage from "./pages/upload";
import AnalyzePage from "./pages/analyze";
import QAChatPage from "./pages/qachat";

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/analyze/:id" element={<AnalyzePage />} />
        <Route path="/qa/:id" element={<QAChatPage />} />
      </Routes>
    </Router>
  );
};

export default App;
