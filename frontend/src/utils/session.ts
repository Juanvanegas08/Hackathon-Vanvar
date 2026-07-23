const leadIdKey = 'casalista:lead-id'
export const getSessionLeadId = () => sessionStorage.getItem(leadIdKey)
export const setSessionLeadId = (leadId: string) => sessionStorage.setItem(leadIdKey, leadId)
export const clearSessionLeadId = () => sessionStorage.removeItem(leadIdKey)
