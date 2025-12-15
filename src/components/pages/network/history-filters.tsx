import { Search } from 'lucide-react'
import { type Table } from '@tanstack/react-table'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import type { NetworkScan } from './types'

interface HistoryFiltersProps {
    table: Table<NetworkScan>
}

export function HistoryFilters({ table }: HistoryFiltersProps) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Search & Filter</CardTitle>
                <CardDescription>
                    Find specific scans using filters and search
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className='flex items-center space-x-2'>
                    <div className='flex-1'>
                        <div className='relative'>
                            <Search className='text-muted-foreground absolute top-3 left-3 h-4 w-4' />
                            <Input
                                placeholder='Search targets, tools, or scan types...'
                                value={
                                    (table.getColumn('target')?.getFilterValue() as string) ?? ''
                                }
                                onChange={(event) =>
                                    table.getColumn('target')?.setFilterValue(event.target.value)
                                }
                                className='max-w-sm pl-10'
                            />
                        </div>
                    </div>
                    <Select
                        value={
                            (table.getColumn('status')?.getFilterValue() as string) ?? 'all'
                        }
                        onValueChange={(value) =>
                            table
                                .getColumn('status')
                                ?.setFilterValue(value === 'all' ? '' : value)
                        }
                    >
                        <SelectTrigger className='w-[180px]'>
                            <SelectValue placeholder='Filter by status' />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value='all'>All Statuses</SelectItem>
                            <SelectItem value='completed'>Completed</SelectItem>
                            <SelectItem value='running'>Running</SelectItem>
                            <SelectItem value='failed'>Failed</SelectItem>
                            <SelectItem value='submitted'>Submitted</SelectItem>
                            <SelectItem value='stopped'>Stopped</SelectItem>
                        </SelectContent>
                    </Select>
                    <Select
                        value={
                            (table.getColumn('tool')?.getFilterValue() as string) ?? 'all'
                        }
                        onValueChange={(value) =>
                            table
                                .getColumn('tool')
                                ?.setFilterValue(value === 'all' ? '' : value)
                        }
                    >
                        <SelectTrigger className='w-[180px]'>
                            <SelectValue placeholder='Filter by tool' />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value='all'>All Tools</SelectItem>
                            <SelectItem value='nmap'>Nmap</SelectItem>
                            <SelectItem value='zmap'>ZMap</SelectItem>
                            <SelectItem value='masscan'>Masscan</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </CardContent>
        </Card>
    )
}
