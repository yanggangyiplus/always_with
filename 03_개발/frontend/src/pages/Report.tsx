import { useFetch } from '../lib/useFetch'
import { card } from '../components/ui'

export default function Report() {
  const { data, error } = useFetch<{ evaluated: boolean; message?: string }>('/reports/model')
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">모델 성능 리포트</h1>
      {error && <p role="alert">{error}</p>}
      {data && !data.evaluated && <p className={card}>{data.message} 평가를 마치면 지표와 혼동 행렬이 여기에 표시돼요.</p>}
      {data?.evaluated && <pre className={card + ' overflow-x-auto text-sm'}>{JSON.stringify(data, null, 2)}</pre>}
      <p className="text-sm text-slate-600">이 서비스는 의료기기가 아닌 보조 알림 도구이며, 모든 낙상을 감지한다고 보장하지 않아요. 가림, 어두운 조명, 여러 사람이 있는 환경에서는 성능이 떨어질 수 있어요.</p>
    </div>
  )
}
