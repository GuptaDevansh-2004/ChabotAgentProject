import { useEffect, useRef, useState } from "react";
import { type Session } from "../store/chatSlice";
import { Trash2 } from "lucide-react";

export default function Sidebar({
  sessions,
  activeId,
  onCreate,
  onSwitch,
  onDelete,
  updateStatus,
}: {
  sessions: Session[];
  activeId: string | null;
  onCreate: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  updateStatus: (id: string) => void;
}) {

  // Updates the status of newly created sessions
  const seenRef = useRef<Set<string>>(new Set());

  // Stores sessions which are deleting
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const newIds = sessions
      .filter(s => s.new && !seenRef.current.has(s.id))
      .map(s => s.id);

    if (!newIds.length) return;

    newIds.forEach(id => seenRef.current.add(id));

    requestAnimationFrame(() => {
      newIds.forEach(id => updateStatus(id));
    });
  }, [sessions, updateStatus]);

  const handleDelete = (id: string) => {
    // Set id in deleting session ids
    setDeletingIds(prev => new Set(prev).add(id));
    // After animation duration, remove from state or store
    setTimeout(() => {
      onDelete(id); // removes session
      setDeletingIds(prev => {
        const copy = new Set(prev);
        copy.delete(id);
        return copy;
      });
    }, 500);
  }

  return (
    <aside className="w-72 p-1.5 rounded flex flex-col font-sans text-[0.96rem] bg-gradient-to-b from-blue-100 via-sky-100 to-sky-200">
      <button
        onClick={onCreate}
        className="w-full mb-3 p-2 bg-[color:var(--color-primary)] text-white rounded hover:bg-[color:var(--color-secondary)] transition shadow-md cursor-pointer active:scale-96 transform"
      >
        + New Chat
      </button>
      <div className="gap-y-0.5 overflow-y-auto flex-1 shadow-md border border-neutral-50 bg-neutral-50 rounded scrollbar-thin">
        {sessions.map((s) => {
          const isDeleting = deletingIds.has(s.id);
          return (
            <div
              key={s.id}
              className={`
                group flex max-w-[99.5%] items-center justify-between rounded border border-blue-50 
                transform overflow-hidden transition-all duration-400 ease-in-out hover:scale-101 
                ${s.id === activeId ? "bg-indigo-100 shadow-md" : "hover:bg-gray-100 bg-white hover:shadow"} 
                ${s.new ? "max-h-0 scale-x-96 opacity-0 -translate-y-2" : "max-h-[120px] scale-x-100 opacity-100 translate-y-0"}
                ${isDeleting && "bg-zinc-200 p-0 scale-y-94 scale-x-65 opacity-0 ease-in-out duration-500"}
              `}
            >
              <button
                onClick={() => onSwitch(s.id)}
                className="flex-1 text-left p-2 ml-0.5 cursor-pointer"
              >
                {s.title ?? s.id.slice(0, 6)}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm("Delete this chat?")) {
                    handleDelete(s.id);
                  }
                }}
                className="p-2 mr-1.5 text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                title="Delete chat"
              >
                <Trash2 size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
