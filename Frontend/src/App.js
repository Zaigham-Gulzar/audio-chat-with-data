import React, { useState } from "react";
import ChatBox from "./components/ChatBox";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import "./App.css";
import ChatBoxFull from "./components/ChatBoxFull";

function App() {
  const [showChat, setShowChat] = useState(false); // Start with the chat box closed
  console.log("this is my state", showChat);
  const width = "100%";
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/chat" element={<ChatBoxFull />} />
          <Route path="/" element={<ChatBox />} />
          {/* <Route path="/:mediaType/:id" element={<Deatail/>}/> */}
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
