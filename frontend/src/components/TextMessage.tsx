import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { preprocessMarkdown } from "../utils";

/**
 * Generic Markdown renderer for both model and user messages.
 * Preserves all custom styling for headings, paragraphs, lists, links, etc.
 */
export const TextMessage = ({ text, isUser }: { text: string; isUser: boolean }) => {
  const components = !isUser
    ? {
        a: ({ node, ...props }: any) => (
          <a {...props} target="_blank" rel="noopener noreferrer" className="text-black hover:underline" />
        ),
        p: ({ node, ...props }: any) => <p {...props} className="mb-1 sm:mb-1 md:mb-1 leading-relaxed" />,
        li: ({ node, ...props }: any) => <li {...props} className="mb-0.5 sm:mb-1 md:mb-1.5 leading-relaxed list-inside" />,
        ul: ({ node, ...props }: any) => <ul {...props} className="my-2 sm:my-2.5 md:my-3 list-disc pl-5 sm:pl-6 md:pl-7" />,
        ol: ({ node, ...props }: any) => <ol {...props} className="my-2 sm:my-2.5 md:my-3 list-decimal pl-5 sm:pl-6 md:pl-7" />,
        hr: ({ node, ...props }: any) => <hr {...props} className="my-4 border-gray-300" />,
        h1: ({ node, ...props }: any) => <h1 {...props} className="mb-2 sm:mt-2 sm:mb-2 md:mb-3" />,
        h2: ({ node, ...props }: any) => <h2 {...props} className="mb-1 sm:mt-2 sm:mb-2 md:mb-3" />,
        h3: ({ node, ...props }: any) => <h3 {...props} className="mb-1 sm:mt-2 sm:mb-2 md:mb-3" />,
        h4: ({ node, ...props }: any) => <h4 {...props} className="mb-1 sm:mt-2 sm:mb-2 md:mb-3" />,
        h5: ({ node, ...props }: any) => <h5 {...props} className="mb-1 sm:mt-2 sm:mb-2 md:mb-3" />,
        h6: ({ node, ...props }: any) => <h6 {...props} className="mb-1 sm:mt-2 sm:mb-2 md:mb-3" />,
      }
    : {}; // For user messages, no custom overrides needed

  return (
    <div
      className={`prose prose-sm sm:prose md:prose-md lg:prose-lg max-w-none ${
        isUser ? "whitespace-pre-wrap break-words" : "break-words"
      }`}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm, ...(isUser ? [] : [remarkBreaks])]} components={components}>
        {isUser ? text : preprocessMarkdown(text)}
      </ReactMarkdown>
    </div>
  );
}
