import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (_err) {
      // Silently fail - clipboard API may not be available
    }
  }

  return (
    <Button
      variant='ghost'
      size='icon'
      className='h-6 w-6'
      onClick={handleCopy}
    >
      {copied ? (
        <Check className='h-3 w-3 text-green-500' />
      ) : (
        <Copy className='text-muted-foreground h-3 w-3' />
      )}
      <span className='sr-only'>Copy</span>
    </Button>
  )
}
