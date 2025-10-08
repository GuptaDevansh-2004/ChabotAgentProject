import ChatApp from "./components/ChatApp.tsx";

export default function App() {
  return (
    <div className="h-screen flex items-center flex-col w-screen">
      <header className="p-3 bg-[color:var(--color-primary)] text-white font-bold font-mono text-2xl shadow-lg w-full">
        <span className="m-2">Chatbot</span>
      </header>
      <main className="flex-1 p-1 w-[99%] scale-y-98 overflow-hidden shadow-indigo-500 shadow-sm ">
        <ChatApp />
      </main>
    </div>
  );
}