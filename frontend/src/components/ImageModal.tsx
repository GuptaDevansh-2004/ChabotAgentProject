import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ImageModal({
  image,
  relatedPaths,
  onToggleImage,
  handleImageClick,
}: {
  image: { path: string; data: string };
  relatedPaths: string[]; // selected paths
  onToggleImage: (path: string) => void;
  handleImageClick: (src: string) => void;
}) {
  const active = relatedPaths && relatedPaths.includes(image.path);
  return (
    <div key={image.path} className={`border rounded-lg h-full overflow-hidden hover:shadow-md transition ${active ? "border-[color:var(--color-primary)] ring-1 shadow" : "border-black"}`}> 
      <img 
        src={image.data} 
        alt="support" 
        className="w-full h-32 object-cover cursor-zoom-in" 
        onClick={() => handleImageClick(image.data)} 
      />
      <button 
        className={`w-full h-10 text-xs px-2 py-1 cursor-pointer ${active ? "bg-[color:var(--color-primary)] text-white" : "bg-gray-100 text-gray-700"}`} 
        onClick={() => onToggleImage(image.path)}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {active ? "*Tagged! - For Current Query*" : "**Tag It!** - For Current Query"}
        </ReactMarkdown>
      </button>
    </div>
  );
}
