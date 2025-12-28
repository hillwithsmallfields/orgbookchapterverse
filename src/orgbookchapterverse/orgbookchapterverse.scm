(use-modules (ice-9 textual-ports))

(define (file-contents filename)
  (call-with-input-file filename get-string-all))

(define (chapters bulk-text)
  (fold-matches "^\* [A-Za-z 1-3]+" bulk-text 0
                (lambda (match prev)
                  (match:start match)
                  )))

(chapters (file-contents "/home/jcgs/library/bible/kj.org"))
