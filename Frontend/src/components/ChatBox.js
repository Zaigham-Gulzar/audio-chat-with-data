//require("dotenv").config();
import React, { useState, useEffect, useRef } from "react";
import "../custom_styles/ChatBox.css";
import image from "../components/image.png";
import colorImage from "../components/colorkit.png";
import loaderGif from "../public/images/827.gif";
import { v4 as uuidv4 } from "uuid";
import Cookies from "js-cookie";
import { TextareaAutosize } from "@mui/base/TextareaAutosize";
import { useLocation } from "react-router-dom";

function ChatBox() {
  const [isOpen, setIsOpen] = useState(true); // Start with the chat box open
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [userMessage, setUserMessage] = useState("");
  const chatContainerRef = useRef(null);
  const [showChat, setShowChat] = useState(true); // Start with the chat box closed
  const inputRef = useRef(null);
  const [isTextEmpty, setIsTextEmpty] = useState(true);
  const [isLoading, setIsLoading] = useState(false); // Add isLoading state
  const [path, setPath] = useState("/");
  let SessionId = "";
  const maxRows = 4;

  const location = useLocation();
  //const isChatPath = location.pathname === '/chat';

  useEffect(() => {
    // Access the pathname from the location
    const currentPath = location.pathname;
    console.log("Current route:", currentPath);
    setPath(currentPath);
    // Example: Redirect to a different route based on the current path
    if (currentPath === "/chat") {
      // Do something specific for the "/chat" route
    } else {
      // Do something specific for other routes
    }
  }, [location.pathname]);

  console.log("here is path", path);
  useEffect(() => {
    if (userMessage) {
      setMessages([...messages, ...userMessage]);
    }
  }, [userMessage]);
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      // When the chat is open and messages array is empty, add the welcome message
      setMessages([{ text: "Welcome to the chat!", user: "support" }]);
    }
  }, [isOpen, messages]);
  //Cookies code started here
  useEffect(() => {
    // Check if the cookie already exists
    let existingCookie = Cookies.get("SessionCookie");
    if (existingCookie) {
      SessionId = existingCookie;
    } else {
      const randomId = uuidv4();
      Cookies.set("SessionCookie", randomId, { expires: 30 });
      existingCookie = randomId;
    }
  }, []);
  const handleTextareaInput = (e) => {
    const textarea = e.target;
    const characterCount = textarea.value.length;

    const maxCharactersPerRow = 80; // Adjust this based on your design

    const rows = Math.ceil(characterCount / maxCharactersPerRow);

    if (rows > 4) {
      textarea.rows = 4; // Limit the number of visible rows to 4
      textarea.style.overflowY = "scroll"; // Enable vertical scrolling
    } else {
      textarea.rows = rows; // Expand the textarea based on character count
      textarea.style.overflowY = "hidden"; // Disable vertical scrolling
    }

    // Update the state with the new message
    setNewMessage(textarea.value);
  };

  // Cookies code ended here
  const handleSendMessage = async () => {
    console.log(messages);
    if (messages.length === 0) {
      setUserMessage([{ text: "Welcome to the chat!", user: "support" }]);
    }
    if (newMessage.trim() !== "") {
      setIsLoading(true);
      SessionId = Cookies.get("SessionCookie");
      // Add the user message to messages
      setMessages([...messages, { text: newMessage, user: "user" }]);
      const apiUrl = process.env.REACT_APP_CHAT_BOX_API_URL;
      const requestBody = {
        question: newMessage,
        CookiesId: SessionId,
      };

      // Make the API call using mockApiCall
      try {
        const response = await fetch(apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        });
        console.log(response);
        if (response.ok) {
          //const responseData = await mockApiCall(newMessage);
          const responseData = await response.json();
          // Check if the responseData contains files
          if (responseData.references && responseData.references.length > 0) {
            // Construct a message that includes the answer, filename, and URL
            const supportMessage = {
              text: (
                <div style={{ textAlign: "justify" }}>
                  {responseData.answer}
                  <br />
                  {responseData.references.map((file, index) => (
                    <span key={index}>
                      <a
                        href={file.filepath}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {file.filename}
                      </a>
                      {index < responseData.references.length - 1 ? ", " : ""}
                    </span>
                  ))}
                </div>
              ),
              user: "support",
            };

            setUserMessage([supportMessage]);
          } else {
            // If there are no files, just add the text response as a support message
            setUserMessage([{ text: responseData.answer, user: "support" }]);
          }
        } else {
          console.error("Error Response:", response);
          setUserMessage([
            {
              text: "I encountered an error while processing your request.",
              user: "support",
            },
          ]);
        }
      } catch (error) {
        console.error("Error parsing JSON:", error);
        setUserMessage([
          {
            text: "An error occurred while processing the response.",
            user: "support",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
      // Clear the input field
      setNewMessage("");
    }
  };
  ///testing

  ///testing
  // Update the isTextEmpty state based on the text field value
  useEffect(() => {
    setIsTextEmpty(newMessage.trim() === "");
  }, [newMessage]);

  // Scroll to the bottom of the chat container whenever new messages are added
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className={`chat-container ${isOpen ? "open" : ""}`}>
      <div>
        {showChat && (
          <div className="chat-box">
            {console.log("inside the minichatbot", path)}
            <div className="chat-header">
              {/* <div className="chat-title">Koenigsegg AI</div> */}
              <div
                className="chat-close"
                onClick={() => setShowChat(!showChat)}
              >
                <i className="fas fa-times"></i> {/* Close icon */}
              </div>
            </div>
            <div className="chat-messages" ref={chatContainerRef}>
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message ${
                    message.user === "user" ? "user-message" : "support-message"
                  }`}
                >
                  {message.text}
                </div>
              ))}
              {isLoading && (
                <div className="message support-message">
                  <img
                    src={loaderGif} // Replace with the path to your loading GIF
                    alt="Loading..."
                    className="loading-gif"
                  />
                </div>
              )}
            </div>
            {isOpen && (
              <div className="chat-input">
                <TextareaAutosize
                  maxRows={4}
                  className="textAreaAS"
                  aria-label="Demo input"
                  placeholder="Type your message..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  style={{
                    width: "300px",
                    borderRadius: "8px",
                    border: "none",
                    outline: "none",
                    resize: "none",
                    maxHeight: "80px",
                    overflowY: "auto",
                    maxRows: 4,
                    padding: "5px 0", // Adjust the vertical padding
                  }}
                />
                {isTextEmpty ? (
                  <img
                    src={image}
                    alt="Send"
                    className="send-image"
                    style={{
                      height: "24px",
                      marginTop: "4px",
                      marginLeft: "10px",
                    }}
                  />
                ) : (
                  <img
                    src={colorImage}
                    alt="Send"
                    className="send-image"
                    style={{
                      height: "24px",
                      marginTop: "4px",
                      marginLeft: "10px",
                    }}
                    onClick={handleSendMessage}
                  />
                )}
              </div>
            )}
          </div>
        )}

        <button
          className={`chat-button ${
            showChat && path !== "/chat" ? "open" : ""
          }`}
          onClick={() => setShowChat(!showChat)}
          style={{ display: path === "/chat" ? "none" : "block" }}
        >
          {showChat && path !== "/chat" ? (
            <i className="fas fa-times"></i> /* Close icon */
          ) : (
            <i className="fas fa-comment"></i> /* Chat icon */
          )}
        </button>
      </div>
    </div>
  );
}

function mockApiCall(newMessage) {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        answer:
          "Customize the widget  of the widget and the avatar it will use. Of course, feel free to change the styles the widget will have in the CSSCustomize the widget to match your app design! You can add both props to manage the title of the widget and the avatar it will use. Of course, feel free to change the styles the widget will have in the CSS",
        references: [
          {
            filename: "UserData1.pdf",
            Url: "http://example.com/userdata1.pdf",
          },
          {
            filename: "UserData2.docx",
            Url: "http://example.com/userdata2.docx",
          },
        ],
      });
    }, 1000); // Simulate a 1-second delay to mimic API response time
  });
}

export default ChatBox;
