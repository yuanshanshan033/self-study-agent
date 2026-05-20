import { Navbar } from "./components/Navbar";
import { NoteLibrary } from "./components/NoteLibrary";
import { ChatWindow } from "./components/ChatWindow";

/**
 * 主应用组件
 * 整合导航栏、笔记库和对话窗口
 */
function App() {
  return (
    <div className="app">
      {/* 背景图 */}
      <div className="app-background" />
      
      {/* 顶部导航栏 */}
      <Navbar />
      
      {/* 主内容区域 */}
      <main className="app-main">
        <div className="app-container">
          {/* 左侧笔记库 */}
          <div className="app-left">
            <NoteLibrary />
          </div>
          
          {/* 右侧对话窗口 */}
          <div className="app-right">
            <ChatWindow />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
