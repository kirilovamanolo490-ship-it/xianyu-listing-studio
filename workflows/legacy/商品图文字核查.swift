import Foundation
import Vision
import AppKit
let args = CommandLine.arguments
let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[1]))) as! [String:Any]
let records = manifest["images"] as! [[String:Any]]
var out = [[String:Any]]()
for row in records {
  let path = row["output_file"] as! String
  if !FileManager.default.fileExists(atPath:path) { continue }
  let req = VNRecognizeTextRequest()
  req.recognitionLevel = .accurate
  req.recognitionLanguages = ["zh-Hans", "en-US"]
  req.usesLanguageCorrection = false
  let handler = VNImageRequestHandler(url:URL(fileURLWithPath:path),options:[:])
  try handler.perform([req])
  let lines = (req.results ?? []).compactMap { o -> [String:Any]? in
    guard let c = o.topCandidates(1).first else { return nil }
    return ["text":c.string,"confidence":c.confidence,"x":o.boundingBox.origin.x,"y":o.boundingBox.origin.y,"width":o.boundingBox.width,"height":o.boundingBox.height]
  }
  out.append(["id":row["id"]!,"file":path,"lines":lines])
}
let data = try JSONSerialization.data(withJSONObject:out,options:[.prettyPrinted,.sortedKeys])
try data.write(to:URL(fileURLWithPath:args[2]))
print("OCR inspected \(out.count) product images")
