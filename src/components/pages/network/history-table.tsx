import { useState, useMemo } from 'react'
import {
    type ColumnDef,
    type ColumnFiltersState,
    type SortingState,
    type VisibilityState,
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from '@tanstack/react-table'
import {
    Eye,
    Download,
    RefreshCw,
    ChevronDown,
    ArrowUpDown,
    Trash2,
    Network,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table'
import { CopyButton } from '@/components/custom/copy-button'
import type { NetworkScan } from './types'
import { DateBadge, StatusBadge, ToolBadge } from './history-badges'
import { HistoryFilters } from './history-filters'
import { formatRelativeDate } from './history-utils'

interface HistoryTableProps {
    scans: NetworkScan[]
    isConnected: boolean
    isRefreshing: boolean
    onRefresh: () => void
    onViewResults: (scan: NetworkScan) => void
    onDownload: (scan: NetworkScan) => void
    onDelete: (jobId: string) => Promise<void>
}

export function HistoryTable({
    scans,
    isConnected,
    isRefreshing,
    onRefresh,
    onViewResults,
    onDownload,
    onDelete,
}: HistoryTableProps) {
    const [sorting, setSorting] = useState<SortingState>([])
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
    const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
    const [rowSelection, setRowSelection] = useState({})

    const columns: ColumnDef<NetworkScan>[] = useMemo(
        () => [
            {
                accessorKey: 'created_at',
                header: ({ column }) => (
                    <Button
                        variant='ghost'
                        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                        className='px-0'
                    >
                        Date
                        <ArrowUpDown className='ml-2 h-4 w-4' />
                    </Button>
                ),
                cell: ({ row }) => <DateBadge date={row.getValue('created_at')} />,
                sortingFn: (rowA, rowB) => {
                    const dateA = new Date(rowA.getValue('created_at'))
                    const dateB = new Date(rowB.getValue('created_at'))
                    return dateB.getTime() - dateA.getTime()
                },
            },
            {
                accessorKey: 'target',
                header: 'Target',
                cell: ({ row }) => (
                    <div className='flex flex-col gap-1'>
                        <span className='font-medium'>{row.getValue('target')}</span>
                        <span className='text-muted-foreground text-xs'>
                            {formatRelativeDate(row.original.created_at)}
                        </span>
                    </div>
                ),
                filterFn: 'includesString',
            },
            {
                accessorKey: 'tool',
                header: 'Tool',
                cell: ({ row }) => <ToolBadge tool={row.getValue('tool')} />,
                filterFn: 'equals',
            },
            {
                accessorKey: 'scan_type',
                header: 'Scan Type',
                cell: ({ row }) => (
                    <span className='text-muted-foreground text-sm capitalize'>
                        {row.getValue('scan_type')}
                    </span>
                ),
            },
            {
                accessorKey: 'status',
                header: 'Status',
                cell: ({ row }) => <StatusBadge status={row.getValue('status')} />,
                filterFn: 'equals',
            },
            {
                accessorKey: 'job_id',
                header: 'Job ID',
                cell: ({ row }) => (
                    <div className='flex items-center gap-2'>
                        <code className='bg-muted rounded px-2 py-1 font-mono text-xs'>
                            {(row.getValue('job_id') as string).slice(0, 8)}...
                        </code>
                        <CopyButton text={row.getValue('job_id')} />
                    </div>
                ),
            },
            {
                id: 'actions',
                header: () => <span className='sr-only'>Actions</span>,
                cell: ({ row }) => (
                    <div className='flex items-center justify-end gap-1'>
                        <Button
                            variant='ghost'
                            size='icon'
                            onClick={() => onViewResults(row.original)}
                            disabled={
                                row.original.status !== 'completed' || !row.original.results
                            }
                            title='View Results'
                        >
                            <Eye className='h-4 w-4' />
                        </Button>
                        <Button
                            variant='ghost'
                            size='icon'
                            onClick={() => onDownload(row.original)}
                            disabled={
                                row.original.status !== 'completed' || !row.original.results
                            }
                            title='Download Results'
                        >
                            <Download className='h-4 w-4' />
                        </Button>
                        <Button
                            variant='ghost'
                            size='icon'
                            onClick={() => onDelete(row.original.job_id)}
                            title='Delete Scan'
                            className='text-red-600 hover:bg-red-50 hover:text-red-700'
                        >
                            <Trash2 className='h-4 w-4' />
                        </Button>
                    </div>
                ),
            },
        ],
        [onViewResults, onDownload, onDelete]
    )

    const table = useReactTable({
        data: scans,
        columns,
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        onColumnVisibilityChange: setColumnVisibility,
        onRowSelectionChange: setRowSelection,
        state: {
            sorting,
            columnFilters,
            columnVisibility,
            rowSelection,
        },
    })

    return (
        <div className='space-y-4'>
            <HistoryFilters table={table} />

            <Card>
                <CardHeader className='flex flex-row items-center justify-between'>
                    <CardTitle className='flex items-center gap-2'>
                        <Network className='h-5 w-5' />
                        Scan History
                    </CardTitle>
                    <Button
                        variant='outline'
                        size='sm'
                        onClick={onRefresh}
                        disabled={isRefreshing || !isConnected}
                    >
                        <RefreshCw
                            className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
                        />
                        Refresh
                    </Button>
                </CardHeader>
                <CardContent>
                    {scans.length === 0 ? (
                        <div className='py-12 text-center'>
                            <Network className='text-muted-foreground mx-auto mb-4 h-12 w-12' />
                            <h3 className='text-lg font-medium'>No scans found</h3>
                            <p className='text-muted-foreground'>
                                Start a new network scan to see results here.
                            </p>
                        </div>
                    ) : (
                        <div className='space-y-4'>
                            <div className='rounded-md border'>
                                <Table>
                                    <TableHeader>
                                        {table.getHeaderGroups().map((headerGroup) => (
                                            <TableRow key={headerGroup.id}>
                                                {headerGroup.headers.map((header) => (
                                                    <TableHead key={header.id}>
                                                        {header.isPlaceholder
                                                            ? null
                                                            : flexRender(
                                                                header.column.columnDef.header,
                                                                header.getContext()
                                                            )}
                                                    </TableHead>
                                                ))}
                                            </TableRow>
                                        ))}
                                    </TableHeader>
                                    <TableBody>
                                        {table.getRowModel().rows?.length ? (
                                            table.getRowModel().rows.map((row) => (
                                                <TableRow
                                                    key={row.id}
                                                    data-state={row.getIsSelected() && 'selected'}
                                                >
                                                    {row.getVisibleCells().map((cell) => (
                                                        <TableCell key={cell.id}>
                                                            {flexRender(
                                                                cell.column.columnDef.cell,
                                                                cell.getContext()
                                                            )}
                                                        </TableCell>
                                                    ))}
                                                </TableRow>
                                            ))
                                        ) : (
                                            <TableRow>
                                                <TableCell
                                                    colSpan={columns.length}
                                                    className='h-24 text-center'
                                                >
                                                    No results.
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </div>

                            <div className='flex items-center justify-between'>
                                <span className='text-muted-foreground text-sm'>
                                    {table.getFilteredRowModel().rows.length} scan(s) found
                                </span>
                                <div className='flex items-center space-x-2'>
                                    <Button
                                        variant='outline'
                                        size='sm'
                                        onClick={() => table.setPageIndex(0)}
                                        disabled={!table.getCanPreviousPage()}
                                    >
                                        <span className='sr-only'>Go to first page</span>
                                        <ChevronDown className='h-4 w-4 rotate-90' />
                                    </Button>
                                    <Button
                                        variant='outline'
                                        size='sm'
                                        onClick={() => table.previousPage()}
                                        disabled={!table.getCanPreviousPage()}
                                    >
                                        Previous
                                    </Button>
                                    <span className='text-sm'>
                                        Page {table.getState().pagination.pageIndex + 1} of{' '}
                                        {table.getPageCount()}
                                    </span>
                                    <Button
                                        variant='outline'
                                        size='sm'
                                        onClick={() => table.nextPage()}
                                        disabled={!table.getCanNextPage()}
                                    >
                                        Next
                                    </Button>
                                    <Button
                                        variant='outline'
                                        size='sm'
                                        onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                                        disabled={!table.getCanNextPage()}
                                    >
                                        <span className='sr-only'>Go to last page</span>
                                        <ChevronDown className='h-4 w-4 -rotate-90' />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
