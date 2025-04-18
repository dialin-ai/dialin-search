import React, { useContext } from "react";
import { Modal } from "@/components/Modal";
import { AgenticToggle } from "./AgenticToggle";
import { SettingsContext } from "@/components/settings/SettingsProvider";
import { useUser } from "@/components/user/UserProvider";
import { LLMSelector } from "@/components/llm/LLMSelector";
import { LlmManager, getDisplayNameForModel } from "@/lib/hooks";
import { getProviderIcon } from "@/app/admin/configuration/llm/interfaces";
import { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import { IconProps } from "@/components/icons/icons";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { structureValue } from "@/lib/llm/utils";

// Create a wrapper for the Settings icon that matches the expected interface
const SettingsIconWrapper = ({ size, className }: IconProps): JSX.Element => {
  return <Settings size={size} className={className} />;
};

interface ChatSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  proSearchEnabled: boolean;
  setProSearchEnabled: (enabled: boolean) => void;
  maxSubQuestions?: number;
  setMaxSubQuestions?: (count: number) => void;
  llmManager: LlmManager;
  llmProviders: LLMProviderDescriptor[];
}

export function ChatSettingsModal({
  isOpen,
  onClose,
  proSearchEnabled,
  setProSearchEnabled,
  maxSubQuestions,
  setMaxSubQuestions,
  llmManager,
  llmProviders,
}: ChatSettingsModalProps) {
  const settings = useContext(SettingsContext);
  const { isAdmin } = useUser();

  const handleSubQuestionCountChange = (value: string) => {
    setMaxSubQuestions?.(parseInt(value));
  };
  
  const handleLlmSelect = (newLlm: string | null) => {
    if (newLlm && llmManager) {
      // Create a llm descriptor from the selected model
      const parts = newLlm.split('__');
      if (parts.length === 3) {
        const [name, provider, modelName] = parts;
        llmManager.updateCurrentLlm({
          name,
          provider,
          modelName
        });
      }
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      title="Chat Settings"
      onOutsideClick={onClose}
      width="w-11/12 max-w-md"
    >
      <div className="flex flex-col space-y-6">
        <div>
          <h3 className="text-lg font-medium mb-2">Model Selection</h3>
          <LLMSelector
            llmProviders={llmProviders}
            currentLlm={llmManager?.currentLlm ? structureValue(llmManager?.currentLlm.name, llmManager?.currentLlm.provider, llmManager?.currentLlm.modelName) : null}
            onSelect={handleLlmSelect}
            requiresImageGeneration={false}
          />
        </div>

        <Separator />

        <div>
          <h3 className="text-lg font-medium mb-2">Search Settings</h3>
          {settings?.settings.pro_search_enabled && (
            <div className="flex flex-col space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Agent Search</h4>
                  <p className="text-sm text-neutral-500">
                    Use AI agents to break down questions for more thorough results
                  </p>
                </div>
                <div className="flex justify-end">
                  <AgenticToggle
                    proSearchEnabled={proSearchEnabled}
                    setProSearchEnabled={setProSearchEnabled}
                    maxSubQuestions={maxSubQuestions}
                    setMaxSubQuestions={setMaxSubQuestions}
                    inModal={true}
                  />
                </div>
              </div>

              {isAdmin && proSearchEnabled && setMaxSubQuestions && (
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Maximum Subquestions</h4>
                    <p className="text-sm text-neutral-500">
                      Admin setting for the number of decomposed questions (2-5)
                    </p>
                  </div>
                  <div className="flex items-center">
                    <Select 
                      value={maxSubQuestions?.toString() || (settings?.settings.max_sub_questions || "3").toString()} 
                      onValueChange={handleSubQuestionCountChange}
                    >
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="2">2</SelectItem>
                        <SelectItem value="3">3</SelectItem>
                        <SelectItem value="4">4</SelectItem>
                        <SelectItem value="5">5</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </Modal>
  );
} 