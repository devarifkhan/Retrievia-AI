import { ChatInterface } from "@/components/chat/ChatInterface";

interface Props {
  params: { id: string };
}

export default function ChatThreadPage({ params }: Props) {
  return <ChatInterface threadId={params.id} />;
}
