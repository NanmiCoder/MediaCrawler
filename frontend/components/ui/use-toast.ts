// Simple toast implementation for demo purposes
export function useToast() {
  const toast = ({ title, description, variant }: {
    title: string
    description: string
    variant?: string
  }) => {
    if (variant === "destructive") {
      alert(`Error: ${title}\n${description}`)
    } else {
      alert(`${title}\n${description}`)
    }
  }
  
  return { toast }
} 