import {quantity} from './pantry'

export function eventLabel(type: string, note = ''): string {
    const reason = note.split(' ')[0]!
    if (type === 'remove') return ({discarded: 'Thrown out', spoiled: 'Spoiled', donated: 'Given away', other: 'Removed'} as Record<string, string>)[reason] || 'Used'
    return ({add: 'Added', move: 'Moved', count: 'Count adjustment', edit: 'Details edited', undo: 'Reversal'} as Record<string, string>)[type] || type
}

export function activityText(event: any): string {
    const unit = event.unit ? {id: event.unit.id, name: event.unit.name, pluralName: event.unit.plural_name} : null
    const change = event.delta ? `${event.delta > 0 ? '+' : '−'}${quantity(Math.abs(event.delta), unit)}` : ''
    const from = event.old_location?.name || 'Unassigned'
    const to = event.new_location?.name || 'Unassigned'
    const place = event.old_location?.id !== event.new_location?.id ? `${from} → ${to}` : to
    const reversal = event.type === 'undo' ? event.note.replace(/^undid #/, 'Reverses activity #') : ''
    return [change, place, reversal].filter(Boolean).join(' · ')
}
