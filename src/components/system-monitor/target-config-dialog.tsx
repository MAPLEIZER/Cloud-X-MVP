import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Pencil } from 'lucide-react'

interface TargetConfigDialogProps {
    targetSystem: string
    tempTarget: string
    isOpen: boolean
    onOpenChange: (open: boolean) => void
    onTempTargetChange: (value: string) => void
    onSave: () => void
}

export function TargetConfigDialog({
    targetSystem,
    tempTarget,
    isOpen,
    onOpenChange,
    onTempTargetChange,
    onSave,
}: TargetConfigDialogProps) {
    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogTrigger asChild>
                <Button
                    variant='ghost'
                    size='icon'
                    className='text-muted-foreground hover:text-foreground ml-2 h-6 w-6'
                    onClick={(e) => {
                        e.stopPropagation()
                        onTempTargetChange(targetSystem)
                    }}
                >
                    <Pencil className='h-3.5 w-3.5' />
                </Button>
            </DialogTrigger>
            <DialogContent onClick={(e) => e.stopPropagation()}>
                <DialogHeader>
                    <DialogTitle>Configure Monitor Target</DialogTitle>
                    <DialogDescription>
                        Enter the IP address or hostname of the system you want to monitor.
                    </DialogDescription>
                </DialogHeader>
                <div className='grid gap-4 py-4'>
                    <div className='grid grid-cols-4 items-center gap-4'>
                        <Input
                            id='target'
                            value={tempTarget}
                            onChange={(e) => onTempTargetChange(e.target.value)}
                            className='col-span-4'
                            placeholder='e.g., 192.168.1.100'
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant='outline' onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={onSave}>Save Changes</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
